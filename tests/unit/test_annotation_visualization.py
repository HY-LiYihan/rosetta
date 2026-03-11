import unittest

from app.ui.viewmodels.annotation_visualization import annotation_to_colored_html


class TestAnnotationVisualization(unittest.TestCase):
    def test_render_colored_annotation_html(self):
        html = annotation_to_colored_html("[supper]{nominalization} and [!主语省略]{reference}")
        self.assertIn("supper", html)
        self.assertIn("主语省略", html)
        self.assertNotIn("[supper]", html)
        self.assertNotIn("[!主语省略]", html)
        self.assertIn("|nominalization", html)
        self.assertIn("|reference", html)
        self.assertIn("background:", html)

    def test_two_labels_include_green_and_red_hues(self):
        html = annotation_to_colored_html("[a]{x} [b]{y}")
        self.assertIn("hsl(142", html)
        self.assertIn("hsl(0", html)


if __name__ == "__main__":
    unittest.main()
