package main

import (
	"image/color"
	"log"
	"math"

	"github.com/hajimehoshi/ebiten/v2"
)

type Game struct {
	distance float64
	speed    float64
	size     float64
}

func triangleWave(value, max float64) float64 {
	if max <= 0 {
		return 0
	}

	period := max * 2
	m := math.Mod(value, period)

	if m < 0 {
		m += period
	}

	if m <= max {
		return m
	}

	return period - m
}

func (g *Game) Update() error {
	dt := 1.0 / 60.0
	acceleration := 20.0

	g.distance += g.speed * dt
	g.speed += g.speed * (acceleration / 100.0) * dt

	if ebiten.IsKeyPressed(ebiten.KeyEscape) {
		return ebiten.Termination
	}

	return nil
}

func (g *Game) Draw(screen *ebiten.Image) {
	screen.Fill(color.White)

	w, h := screen.Bounds().Dx(), screen.Bounds().Dy()

	x := triangleWave(g.distance, float64(w)-g.size)
	y := (float64(h) - g.size) / 2

	img := ebiten.NewImage(int(g.size), int(g.size))
	img.Fill(color.Black)

	op := &ebiten.DrawImageOptions{}
	op.GeoM.Translate(x, y)

	screen.DrawImage(img, op)
}

func (g *Game) Layout(outsideWidth, outsideHeight int) (int, int) {
	return 1000, 600
}

func main() {
	ebiten.SetWindowSize(1000, 600)
	ebiten.SetWindowTitle("Square")

	game := &Game{
		speed: 600,
		size:  50,
	}

	if err := ebiten.RunGame(game); err != nil {
		log.Fatal(err)
	}
}
