use macroquad::prelude::*;

fn triangle_wave(value: f32, max: f32) -> f32 {
    if max <= 0.0 {
        return 0.0;
    }

    let period = max * 2.0;
    let mut m = value % period;

    if m < 0.0 {
        m += period;
    }

    if m <= max {
        m
    } else {
        period - m
    }
}

#[macroquad::main("Square")]
async fn main() {
    let size = 50.0;
    let mut distance = 0.0;
    let mut speed = 600.0;
    let acceleration = 20.0; // procent na sekundę

    loop {
        let dt = get_frame_time();

        distance += speed * dt;
        speed += speed * (acceleration / 100.0) * dt;

        let max_x = screen_width() - size;
        let y = (screen_height() - size) / 2.0;
        let x = triangle_wave(distance, max_x);

        clear_background(WHITE);
        draw_rectangle(x, y, size, size, BLACK);

        if is_key_pressed(KeyCode::Escape) {
            break;
        }

        next_frame().await;
    }
}