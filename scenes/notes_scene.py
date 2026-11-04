"""Five-page course notes screen loaded from the selected course JSON file."""

from typing import TYPE_CHECKING, Any

import pygame

from scenes.base_scene import BaseScene
from ui.components import Button, Card
from ui.theme import COLORS, draw_rounded_rect, draw_text, font
from utils.content import ContentLoadError, load_course
from voice.commands import VoiceCommand

if TYPE_CHECKING:
    from core.game import Game


class NotesScene(BaseScene):
    """Present topic notes and examples before the player starts the maze."""

    def __init__(self, game: "Game") -> None:
        """Load the selected course notes and prepare page-navigation controls."""
        super().__init__(game)
        self.page_index = 0
        self.topics: list[dict[str, Any]] = []
        self.load_error = ""
        self._back_button = Button(pygame.Rect(0, 0, 144, 44), "BACK", COLORS["text_muted"])
        self._next_button = Button(pygame.Rect(0, 0, 180, 48), "NEXT TOPIC", COLORS["purple"])
        self._start_button = Button(pygame.Rect(0, 0, 220, 48), "START MAZE", COLORS["cyan"])
        self._notes_view_rect = pygame.Rect(0, 0, 0, 0)
        self._notes_scroll = 0
        self._load_topics()

    def handle_command(self, command: VoiceCommand) -> None:
        """Navigate note pages or request the maze from the final page."""
        if command.action == "next":
            self._next_page()
        elif command.action == "back":
            self._previous_page()
        elif command.action == "start_maze":
            self._start_maze()

    def handle_event(self, event: pygame.event.Event) -> None:
        """Handle mouse page navigation and the course-selection back action."""
        self._layout_buttons()
        if (
            event.type == pygame.MOUSEWHEEL
            and self._notes_view_rect.collidepoint(pygame.mouse.get_pos())
        ):
            self._notes_scroll = max(0, self._notes_scroll - event.y * 42)
            return
        if self._back_button.handle_event(event):
            from scenes.level_scene import LevelScene

            self.game.scenes.change(LevelScene(self.game))
            return
        if self._next_button.handle_event(event):
            self._next_page()
            return
        if self._start_button.handle_event(event):
            self._start_maze()

    def draw(self, surface: pygame.Surface) -> None:
        """Render the current note, example block, page number, and navigation."""
        domain = self.game.state.domain or "Course"
        level = self.game.state.level or "Notes"
        self.draw_shell(
            surface,
            "Step 3 of 3  •  Learn",
            f"{domain} / {level}",
            "Study each topic, then use its knowledge to unlock a maze door.",
        )
        width, height = surface.get_size()
        self._layout_buttons()
        page_label = f"{self.page_index + 1} / 5"
        draw_text(
            surface,
            f"TOPIC  {page_label}",
            (width - 72, 150),
            size=15,
            color=COLORS["cyan"],
            role="heading",
            align="topright",
        )

        content_rect = pygame.Rect(68, 170, width - 136, height - 330)
        if self.load_error:
            Card(
                content_rect,
                title="Course notes aren’t available yet",
                body=[
                    self.load_error,
                    "The matching course JSON is added in the content phase.",
                    "Go back to choose another course or try again after content is installed.",
                ],
                accent=COLORS["red"],
            ).draw(surface)
        elif not self.topics:
            Card(
                content_rect,
                title="No course topics found",
                body=["The selected course file does not contain its five topic pages."],
                accent=COLORS["red"],
            ).draw(surface)
        else:
            topic = self.topics[self.page_index]
            self._draw_topic(surface, content_rect, topic)

        self._back_button.rect.topleft = (68, height - 126)
        self._back_button.draw(surface)
        self._next_button.rect.topleft = (width - 68 - 190 - 232, height - 126)
        self._next_button.draw(surface)
        self._start_button.rect.topleft = (width - 68 - 220, height - 126)
        self._start_button.draw(surface)
        if self.page_index >= 4:
            draw_text(
                surface,
                "Say “start maze” when you’re ready.",
                (width // 2, height - 66),
                size=14,
                color=COLORS["text_muted"],
                align="center",
            )

    def _draw_topic(
        self,
        surface: pygame.Surface,
        rect: pygame.Rect,
        topic: dict[str, Any],
    ) -> None:
        """Display scrollable lesson bullets beside complete code and output."""
        shadow = rect.move(0, 7)
        pygame.draw.rect(surface, COLORS["black"], shadow, border_radius=20)
        draw_rounded_rect(
            surface,
            rect,
            COLORS["surface"],
            radius=20,
            border_color=COLORS["border"],
        )
        pygame.draw.rect(
            surface,
            COLORS["purple"],
            pygame.Rect(rect.x + 1, rect.y + 18, 4, rect.height - 36),
            border_radius=3,
        )
        draw_text(
            surface,
            str(topic["title"]),
            (rect.x + 26, rect.y + 20),
            size=22,
            role="heading",
        )

        inner = rect.inflate(-48, -90)
        notes_width = int(inner.width * 0.42)
        notes_rect = pygame.Rect(inner.x, inner.y + 2, notes_width, inner.height)
        self._notes_view_rect = notes_rect
        right_rect = pygame.Rect(
            notes_rect.right + 18,
            inner.y + 2,
            inner.right - notes_rect.right - 18,
            inner.height,
        )
        draw_rounded_rect(surface, notes_rect, (13, 18, 33), radius=13)
        draw_text(
            surface,
            "KEY IDEAS  •  SCROLL TO REVIEW",
            (notes_rect.x + 16, notes_rect.y + 12),
            size=11,
            color=COLORS["cyan"],
            role="heading",
        )
        note_font = font(14)
        note_line_height = 18
        note_y = notes_rect.y + 38
        note_max_width = notes_rect.width - 52
        wrapped_notes = [
            _wrap_to_width(str(note), note_font, note_max_width)
            for note in topic["notes"]
        ]
        total_note_height = sum(
            max(1, len(lines)) * note_line_height + 6 for lines in wrapped_notes
        )
        max_scroll = max(
            0,
            total_note_height - (notes_rect.height - 48),
        )
        self._notes_scroll = min(self._notes_scroll, max_scroll)
        previous_clip = surface.get_clip()
        surface.set_clip(
            pygame.Rect(
                notes_rect.x + 8,
                notes_rect.y + 35,
                notes_rect.width - 16,
                max(1, notes_rect.height - 43),
            )
        )
        note_y -= self._notes_scroll
        for lines in wrapped_notes:
            draw_text(
                surface,
                "•",
                (notes_rect.x + 16, note_y),
                size=17,
                color=COLORS["purple"],
                role="heading",
            )
            for line_index, line in enumerate(lines):
                draw_text(
                    surface,
                    line,
                    (notes_rect.x + 34, note_y + line_index * note_line_height),
                    size=15,
                    color=COLORS["text_muted"],
                )
            note_y += max(1, len(lines)) * note_line_height + 6
        surface.set_clip(previous_clip)
        if max_scroll:
            track_rect = pygame.Rect(
                notes_rect.right - 10,
                notes_rect.y + 38,
                4,
                max(1, notes_rect.height - 48),
            )
            pygame.draw.rect(surface, COLORS["surface_light"], track_rect, border_radius=3)
            thumb_height = max(
                24,
                int(track_rect.height * (track_rect.height / total_note_height)),
            )
            thumb_travel = track_rect.height - thumb_height
            thumb_y = track_rect.y + int(
                thumb_travel * self._notes_scroll / max_scroll
            )
            pygame.draw.rect(
                surface,
                COLORS["purple"],
                pygame.Rect(track_rect.x, thumb_y, track_rect.width, thumb_height),
                border_radius=3,
            )

        example = str(topic["example"])
        output = str(topic["example_output"])
        output_lines = _wrap_to_width(output, font(12, "mono"), right_rect.width - 30)
        output_height = min(
            max(66, 38 + len(output_lines) * 15),
            max(66, right_rect.height // 3),
        )
        output_rect = pygame.Rect(
            right_rect.x,
            right_rect.bottom - output_height,
            right_rect.width,
            output_height,
        )
        code_rect = pygame.Rect(
            right_rect.x,
            right_rect.y,
            right_rect.width,
            max(70, output_rect.y - right_rect.y - 12),
        )
        draw_rounded_rect(
            surface,
            code_rect,
            (12, 17, 32),
            radius=12,
            border_color=COLORS["border"],
        )
        draw_text(
            surface,
            "EXAMPLE CODE",
            (code_rect.x + 14, code_rect.y + 10),
            size=11,
            color=COLORS["cyan"],
            role="heading",
        )
        code_font_size = 12
        code_line_height = 14
        code_font = font(code_font_size, "mono")
        code_lines = _wrap_code(example, code_font, code_rect.width - 28)
        while (
            len(code_lines) * code_line_height > code_rect.height - 38
            and code_font_size > 9
        ):
            code_font_size -= 1
            code_line_height = code_font_size + 2
            code_font = font(code_font_size, "mono")
            code_lines = _wrap_code(example, code_font, code_rect.width - 28)
        for line_index, line in enumerate(code_lines):
            draw_text(
                surface,
                line,
                (code_rect.x + 14, code_rect.y + 31 + line_index * code_line_height),
                size=code_font_size,
                color=COLORS["green"] if "=" in line else COLORS["text"],
                role="mono",
            )
        draw_rounded_rect(
            surface,
            output_rect,
            (13, 18, 33),
            radius=12,
            border_color=COLORS["border"],
        )
        draw_text(
            surface,
            "EXPECTED OUTPUT",
            (output_rect.x + 14, output_rect.y + 9),
            size=10,
            color=COLORS["purple"],
            role="heading",
        )
        output_font = font(12, "mono")
        output_lines = _wrap_to_width(output, output_font, output_rect.width - 28)
        output_clip = pygame.Rect(
            output_rect.x + 8,
            output_rect.y + 26,
            output_rect.width - 16,
            max(1, output_rect.height - 32),
        )
        surface.set_clip(output_clip)
        for line_index, line in enumerate(output_lines):
            draw_text(
                surface,
                line,
                (output_rect.x + 14, output_rect.y + 27 + line_index * 15),
                size=12,
                color=COLORS["text"],
                role="mono",
            )
        surface.set_clip(previous_clip)

    def _load_topics(self) -> None:
        """Load and validate exactly five topic pages from the course JSON."""
        domain = self.game.state.domain
        level = self.game.state.level
        if domain is None or level is None:
            self.load_error = "Choose a domain and difficulty before opening notes."
            return
        try:
            self.topics = load_course(domain, level)
        except ContentLoadError as error:
            self.load_error = str(error)

    def _layout_buttons(self) -> None:
        """Keep navigation controls aligned to the current resizable window."""
        width, height = self.game.screen.get_size()
        self._back_button.rect.topleft = (68, height - 126)
        self._next_button.rect.topleft = (width - 68 - 190 - 232, height - 126)
        self._start_button.rect.topleft = (width - 68 - 220, height - 126)

    def _next_page(self) -> None:
        """Advance one topic page without moving past the fifth topic."""
        if self.load_error or not self.topics:
            self.toast.show("Course notes are unavailable.", COLORS["red"])
            return
        self.page_index = min(4, self.page_index + 1)
        self._notes_scroll = 0

    def _previous_page(self) -> None:
        """Return to the previous topic or the difficulty-selection screen."""
        if self.page_index > 0:
            self.page_index -= 1
            self._notes_scroll = 0
            return
        from scenes.level_scene import LevelScene

        self.game.scenes.change(LevelScene(self.game))

    def _start_maze(self) -> None:
        """Open the maze scene when it is available in the next project phase."""
        if len(self.topics) != 5:
            self.toast.show("Load all five course notes before starting.", COLORS["red"])
            return
        if self.page_index < 4:
            self.toast.show("Review all five topics before starting the maze.", COLORS["yellow"])
            return
        try:
            from scenes.maze_scene import MazeScene
        except ModuleNotFoundError as error:
            if error.name != "scenes.maze_scene":
                raise
            self.toast.show("The maze scene is added in the next phase.", COLORS["yellow"])
            return
        self.game.scenes.change(MazeScene(self.game))


def _wrap_to_width(
    text: str,
    text_font: pygame.font.Font,
    max_width: int,
) -> list[str]:
    """Wrap readable prose or output using the active font's pixel width."""
    if not text:
        return [""]
    lines: list[str] = []
    for paragraph in text.splitlines() or [""]:
        current = ""
        for word in paragraph.split():
            candidate = f"{current} {word}".strip()
            if current and text_font.size(candidate)[0] > max_width:
                lines.append(current)
                current = word
            else:
                current = candidate
        lines.append(current)
    return lines


def _wrap_code(
    example: str,
    text_font: pygame.font.Font,
    max_width: int,
) -> list[str]:
    """Wrap every source-code line to the available block width."""
    lines: list[str] = []
    for source_line in example.splitlines() or [""]:
        if not source_line:
            lines.append("")
            continue
        current = ""
        for character in source_line:
            candidate = current + character
            if current and text_font.size(candidate)[0] > max_width:
                lines.append(current)
                current = character
            else:
                current = candidate
        lines.append(current)
    return lines
