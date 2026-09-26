//! Fast native work-marker scanning engine for Koru.
//!
//! Provides pure functions for tokenizing comments, filtering ignore patterns,
//! and scanning directory trees for TODO/FIXME/XXX/HACK markers.

use std::collections::BTreeMap;
use std::fs;
use std::path::Path;

pub const DEFAULT_SCAN_EXCLUDES: &[&str] = &[
    ".git",
    ".worktrees",
    ".subactor",
    "target",
    ".gradle",
    "__pycache__",
    ".venv",
    ".venv-test",
    "venv",
    "node_modules",
    "build",
    "dist",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".code2llm_cache",
    ".playwright-browsers",
];

const MARKERS: &[&[u8]] = &[b"TODO", b"FIXME", b"XXX", b"HACK"];

/// Check if byte at index is a word character (ASCII alphanumeric or underscore).
#[inline]
fn is_word_byte(b: u8) -> bool {
    b.is_ascii_alphanumeric() || b == b'_'
}

/// Count occurrences of marker regex in a given slice of bytes.
/// Matches `\b(TODO|FIXME|XXX|HACK)\b[: ]`.
pub fn count_markers_in_text(bytes: &[u8]) -> usize {
    let mut count = 0;
    let len = bytes.len();

    for &marker in MARKERS {
        let m_len = marker.len();
        if len < m_len + 1 {
            continue;
        }

        let mut idx = 0;
        while idx + m_len < len {
            // Find marker
            if let Some(pos) = bytes[idx..].windows(m_len).position(|w| w == marker) {
                let match_idx = idx + pos;
                // Word boundary check before marker
                let before_ok = match_idx == 0 || !is_word_byte(bytes[match_idx - 1]);
                if before_ok {
                    let after_idx = match_idx + m_len;
                    if after_idx < len {
                        let after_byte = bytes[after_idx];
                        if after_byte == b':' || after_byte == b' ' {
                            count += 1;
                        }
                    }
                }
                idx = match_idx + m_len;
            } else {
                break;
            }
        }
    }
    count
}

#[derive(Copy, Clone, PartialEq, Eq, Debug)]
enum LexState {
    Normal,
    SingleQuote,
    DoubleQuote,
    TripleSingleQuote,
    TripleDoubleQuote,
}

/// Extract Python comment portions from source code.
/// Distinguishes comments (`# ...`) outside single/double/triple quoted strings.
pub fn extract_python_comments(text: &str) -> Vec<&str> {
    let mut comments = Vec::new();
    let bytes = text.as_bytes();
    let mut state = LexState::Normal;
    let mut i = 0;

    while i < bytes.len() {
        match state {
            LexState::Normal => {
                let (next_state, next_i, comment_range) = lex_normal(bytes, i);
                if let Some((start, end)) = comment_range {
                    push_comment(&mut comments, bytes, start, end);
                }
                state = next_state;
                i = next_i;
            }
            LexState::SingleQuote | LexState::DoubleQuote => {
                i = skip_quoted_string(bytes, i, quote_byte(state));
                state = LexState::Normal;
            }
            LexState::TripleSingleQuote | LexState::TripleDoubleQuote => {
                i = skip_triple_quoted_string(bytes, i, quote_byte(state));
                state = LexState::Normal;
            }
        }
    }

    comments
}

/// Quote byte that opens and closes the string literal for a string `state`.
fn quote_byte(state: LexState) -> u8 {
    match state {
        LexState::SingleQuote | LexState::TripleSingleQuote => b'\'',
        LexState::DoubleQuote | LexState::TripleDoubleQuote => b'"',
        LexState::Normal => unreachable!("Normal is not a string literal state"),
    }
}

/// Consume one token from `LexState::Normal` starting at byte `i`.
/// Returns the next state, the next byte index, and the `[start, end)` range
/// of a comment when one was consumed.
fn lex_normal(bytes: &[u8], i: usize) -> (LexState, usize, Option<(usize, usize)>) {
    let b = bytes[i];
    if is_triple_quote(bytes, i, b'"') {
        (LexState::TripleDoubleQuote, i + 3, None)
    } else if is_triple_quote(bytes, i, b'\'') {
        (LexState::TripleSingleQuote, i + 3, None)
    } else if b == b'"' {
        (LexState::DoubleQuote, i + 1, None)
    } else if b == b'\'' {
        (LexState::SingleQuote, i + 1, None)
    } else if b == b'#' {
        let end = comment_line_end(bytes, i);
        (LexState::Normal, end, Some((i, end)))
    } else {
        (LexState::Normal, i + 1, None)
    }
}

/// Byte index just past the last comment character of the line starting at
/// the `#` byte `start`; stops before `\n` or `\r`, or at end of input.
fn comment_line_end(bytes: &[u8], start: usize) -> usize {
    let mut end = start;
    while end < bytes.len() && bytes[end] != b'\n' && bytes[end] != b'\r' {
        end += 1;
    }
    end
}

/// Push the comment spanning `[start, end)` when those bytes are valid UTF-8.
fn push_comment<'a>(comments: &mut Vec<&'a str>, bytes: &'a [u8], start: usize, end: usize) {
    if let Ok(comment) = std::str::from_utf8(&bytes[start..end]) {
        comments.push(comment);
    }
}

/// True when a triple `quote` delimiter starts at byte `i`.
fn is_triple_quote(bytes: &[u8], i: usize, quote: u8) -> bool {
    i + 2 < bytes.len() && bytes[i] == quote && bytes[i + 1] == quote && bytes[i + 2] == quote
}

/// Consume the body of a single-line quoted string starting at `i`.
/// Returns the index just past the closing quote, past the newline that
/// terminates an unterminated literal, or end of input.
fn skip_quoted_string(bytes: &[u8], mut i: usize, quote: u8) -> usize {
    let len = bytes.len();
    while i < len {
        if bytes[i] == b'\\' && i + 1 < len {
            i += 2;
        } else if bytes[i] == quote || bytes[i] == b'\n' {
            return i + 1;
        } else {
            i += 1;
        }
    }
    len
}

/// Consume the body of a triple-quoted string starting at `i`.
/// Returns the index just past the closing triple quote or end of input.
fn skip_triple_quoted_string(bytes: &[u8], mut i: usize, quote: u8) -> usize {
    let len = bytes.len();
    while i + 2 < len {
        if bytes[i] == b'\\' && i + 1 < len {
            i += 2;
        } else if is_triple_quote(bytes, i, quote) {
            return i + 3;
        } else {
            i += 1;
        }
    }
    len
}

/// Count TODO/FIXME/XXX/HACK markers in comments of a source text.
pub fn count_todo_markers(text: &str) -> usize {
    let comments = extract_python_comments(text);
    let mut total = 0;
    for comment in comments {
        total += count_markers_in_text(comment.as_bytes());
    }
    total
}

/// Minimal fnmatch-style glob matching (* and ?).
pub fn glob_match(pattern: &str, text: &str) -> bool {
    let p_bytes = pattern.as_bytes();
    let t_bytes = text.as_bytes();
    let mut p = 0;
    let mut t = 0;
    let mut star_p = None;
    let mut star_t = 0;

    while t < t_bytes.len() {
        if p < p_bytes.len() && (p_bytes[p] == b'?' || p_bytes[p] == t_bytes[t]) {
            p += 1;
            t += 1;
        } else if p < p_bytes.len() && p_bytes[p] == b'*' {
            star_p = Some(p);
            p += 1;
            star_t = t;
        } else if let Some(sp) = star_p {
            p = sp + 1;
            star_t += 1;
            t = star_t;
        } else {
            return false;
        }
    }

    while p < p_bytes.len() && p_bytes[p] == b'*' {
        p += 1;
    }

    p == p_bytes.len()
}

/// Load ignore patterns from `.koruignore`.
pub fn load_koruignore_patterns(project: &Path) -> Vec<String> {
    let ignore_file = project.join(".koruignore");
    if !ignore_file.is_file() {
        return Vec::new();
    }
    let content = match fs::read_to_string(&ignore_file) {
        Ok(c) => c,
        Err(_) => return Vec::new(),
    };

    let mut patterns = Vec::new();
    for line in content.lines() {
        let trimmed = line.trim();
        if trimmed.is_empty() || trimmed.starts_with('#') {
            continue;
        }
        let pattern = if let Some(stripped) = trimmed.strip_prefix("./") {
            stripped
        } else if let Some(stripped) = trimmed.strip_prefix('/') {
            stripped
        } else {
            trimmed
        };
        patterns.push(pattern.to_string());
    }
    patterns
}

/// Check if a relative path matches `.koruignore` patterns.
pub fn is_koruignored(rel_path: &Path, patterns: &[String]) -> bool {
    if patterns.is_empty() {
        return false;
    }

    let rel_str = rel_path.to_string_lossy().replace('\\', "/");
    let file_name = rel_path.file_name().and_then(|n| n.to_str()).unwrap_or("");

    for pattern in patterns {
        if pattern.is_empty() {
            continue;
        }

        if let Some(prefix) = pattern.strip_suffix('/') {
            if rel_str == prefix || rel_str.starts_with(&format!("{prefix}/")) {
                return true;
            }
            continue;
        }

        if glob_match(pattern, &rel_str) {
            return true;
        }

        if !pattern.contains('/') && glob_match(pattern, file_name) {
            return true;
        }
    }

    false
}

/// Configuration options for scanning.
pub struct ScanOptions<'a> {
    pub min_per_file: usize,
    pub max_files_walked: usize,
    pub excludes: &'a [&'a str],
}

impl Default for ScanOptions<'_> {
    fn default() -> Self {
        Self {
            min_per_file: 3,
            max_files_walked: 2_000,
            excludes: DEFAULT_SCAN_EXCLUDES,
        }
    }
}

/// Walk project directory and count marker occurrences meeting threshold.
pub fn count_todo_markers_in_project(
    project: &Path,
    options: &ScanOptions,
) -> BTreeMap<String, usize> {
    let mut counts = BTreeMap::new();
    let koruignore_patterns = load_koruignore_patterns(project);
    let mut walked = 0;

    let mut dirs_to_visit = vec![project.to_path_buf()];

    while let Some(current_dir) = dirs_to_visit.pop() {
        let entries = match fs::read_dir(&current_dir) {
            Ok(e) => e,
            Err(_) => continue,
        };

        for entry in entries.flatten() {
            let path = entry.path();
            let file_name = entry.file_name();
            let name_str = file_name.to_string_lossy();

            // Check default excludes
            if options.excludes.iter().any(|&ex| name_str == ex) {
                continue;
            }

            let rel_path = match path.strip_prefix(project) {
                Ok(r) => r,
                Err(_) => continue,
            };

            if is_koruignored(rel_path, &koruignore_patterns) {
                continue;
            }

            if path.is_dir() {
                dirs_to_visit.push(path);
            } else if path.is_file() {
                // Check extension
                if path.extension().and_then(|ext| ext.to_str()) == Some("py") {
                    walked += 1;
                    if walked > options.max_files_walked {
                        return counts;
                    }

                    if let Ok(text) = fs::read_to_string(&path) {
                        let count = count_todo_markers(&text);
                        if count >= options.min_per_file {
                            counts.insert(rel_path.to_string_lossy().replace('\\', "/"), count);
                        }
                    }
                }
            }
        }
    }

    counts
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_count_markers_basic() {
        let text = "# TODO: fix this\n# FIXME: broken\nx = 1\n# XXX something\n# HACK: fast\n";
        assert_eq!(count_todo_markers(text), 4);
    }

    #[test]
    fn test_ignore_inside_strings() {
        let text = "label = 'TODO: not a comment'\n# TODO: real comment\n";
        assert_eq!(count_todo_markers(text), 1);
    }

    #[test]
    fn test_glob_match() {
        assert!(glob_match("*.py", "test.py"));
        assert!(glob_match("src/*.py", "src/foo.py"));
        assert!(!glob_match("*.py", "test.rs"));
        assert!(glob_match("foo?bar", "fooxbar"));
    }

    #[test]
    fn test_is_koruignored() {
        let patterns = vec!["vendor/".to_string(), "*.tmp".to_string()];
        assert!(is_koruignored(Path::new("vendor/lib.py"), &patterns));
        assert!(is_koruignored(Path::new("scratch.tmp"), &patterns));
        assert!(!is_koruignored(Path::new("src/main.py"), &patterns));
    }
}
