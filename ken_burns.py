from manim import *

# Set custom config BEFORE defining the scene
config.pixel_height = 1920
config.pixel_width = 1080
config.frame_height = 14.4  # default height in manim units
config.frame_width = config.pixel_width * config.frame_height / config.pixel_height

class KenBurnsEffect(Scene):
    def construct(self):
        img = ImageMobject("{{IMAGE_PATH}}")
        img.set_resampling_algorithm(RESAMPLING_ALGORITHMS["bilinear"])

        img.set_height(config.frame_height)
        img.scale(1.2)
        self.add(img)

        self.play(
            img.animate.scale(1.3 / 1.2).shift(UP * 1.2),
            run_time={{RUN_TIME}},
            rate_func=smooth
        )
