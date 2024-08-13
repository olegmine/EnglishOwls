from kivy.app import App
from kivy.uix.gridlayout import GridLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.core.window import Window
from kivy.utils import get_color_from_hex
from kivy.metrics import dp
from kivy.graphics import Color, RoundedRectangle, Ellipse
import sqlite3
from kivy.core.text import LabelBase
from kivy.animation import Animation
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.behaviors import DragBehavior

LabelBase.register(name='PhoneticFont', fn_regular='Fonts/phonetic.ttf')
LabelBase.register(name='Vintage', fn_regular='Fonts/Vintage.otf')

class RoundedButton(Button):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.background_color = [0, 0, 0, 0]
        self.color = get_color_from_hex('#FFFFFF')
        self.bold = True
        with self.canvas.before:
            self.rect_color = Color(*get_color_from_hex('#007AFF'))
            self.rect = RoundedRectangle(size=self.size, pos=self.pos, radius=[dp(10)])
        self.bind(pos=self.update_rect, size=self.update_rect)

    def update_rect(self, *args):
        self.rect.pos = self.pos
        self.rect.size = self.size

    def on_press(self):
        anim = Animation(opacity=0.5, duration=0.1)
        anim.start(self)

    def on_release(self):
        anim = Animation(opacity=1, duration=0.1)
        anim.start(self)

class ThemeButton(FloatLayout):
    def __init__(self, app, **kwargs):
        super().__init__(**kwargs)
        self.app = app
        self.size_hint = (None, None)
        self.size = (dp(60), dp(30))
        with self.canvas:
            self.background_color = Color(*get_color_from_hex('#E0E0E0'))
            self.background = RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(15)])
            self.switch_color = Color(*get_color_from_hex('#FFFFFF'))
            self.switch = Ellipse(pos=(self.x, self.y), size=(dp(30), dp(30)))
        self.bind(pos=self.update_canvas)

    def update_canvas(self, *args):
        self.background.pos = self.pos
        self.background.size = self.size
        self.switch.pos = (self.x, self.y) if self.app.theme == 'light' else (self.x + dp(30), self.y)

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            self.app.toggle_theme()
            return True
        return super().on_touch_down(touch)

class DraggableGrid(DragBehavior, GridLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.drag_distance = dp(20)
        self.drag_rect_x = self.x
        self.drag_rect_y = self.y
        self.drag_rect_width = self.width
        self.drag_rect_height = self.height

class OwlishEnglishApp(App):
    def build(self):
        self.theme = 'light'
        self.conn = sqlite3.connect('words.db', detect_types=sqlite3.PARSE_DECLTYPES)
        self.conn.execute('PRAGMA encoding = "UTF-8"')
        self.cursor = self.conn.cursor()

        self.cursor.execute('''CREATE TABLE IF NOT EXISTS words
                              (id INTEGER PRIMARY KEY, word TEXT, translation TEXT, learned INTEGER, transcription TEXT, mnemonic TEXT)''')

        self.cursor.execute("PRAGMA table_info(words)")
        columns = [column[1] for column in self.cursor.fetchall()]
        if 'transcription' not in columns:
            self.cursor.execute("ALTER TABLE words ADD COLUMN transcription TEXT")
        if 'mnemonic' not in columns:
            self.cursor.execute("ALTER TABLE words ADD COLUMN mnemonic TEXT")
        if 'learned' not in columns:
            self.cursor.execute("ALTER TABLE words ADD COLUMN learned INTEGER DEFAULT 0")

        self.conn.commit()

        self.set_theme_colors()

        self.main_layout = GridLayout(cols=1, spacing=dp(16), padding=dp(24))

        # Theme button
        theme_layout = GridLayout(cols=2, size_hint_y=None, height=dp(48))
        theme_label = Label(text='Тёмная тема', color=self.text_color)
        self.theme_button = ThemeButton(self)
        theme_layout.add_widget(theme_label)
        theme_layout.add_widget(self.theme_button)
        self.main_layout.add_widget(theme_layout)

        # Word display
        self.word_layout = DraggableGrid(cols=1, spacing=dp(8), size_hint_y=None)
        self.word_layout.bind(minimum_height=self.word_layout.setter('height'))

        self.word_label = Label(text='', font_name='Vintage', font_size=dp(32), bold=True, color=self.text_color,
                                size_hint_y=None, height=dp(48))
        self.transcription_label = Label(text='', font_name='PhoneticFont', font_size=dp(18), color=self.text_color,
                                         size_hint_y=None, height=dp(32))
        self.translation_label = Label(text='', font_size=dp(24), color=self.text_color, size_hint_y=None,
                                       height=dp(40), opacity=0)
        self.mnemonic_label = Label(text='', font_size=dp(18), color=self.text_color, size_hint_y=None, height=dp(64),
                                    opacity=0)
        self.learned_status_label = Label(text='', font_size=dp(18), color=self.text_color, size_hint_y=None, height=dp(32))

        self.word_layout.add_widget(self.word_label)
        self.word_layout.add_widget(self.transcription_label)
        self.word_layout.add_widget(self.translation_label)
        self.word_layout.add_widget(self.mnemonic_label)
        self.word_layout.add_widget(self.learned_status_label)

        scroll_view = ScrollView(size_hint=(1, None), size=(Window.width, Window.height * 0.6))
        scroll_view.add_widget(self.word_layout)
        self.main_layout.add_widget(scroll_view)

        # Navigation buttons
        nav_layout = GridLayout(cols=2, size_hint_y=None, height=dp(48), spacing=dp(8))
        prev_word_button = RoundedButton(text='<', size_hint_x=None, width=dp(48))
        prev_word_button.bind(on_release=self.load_previous_word)
        next_word_button = RoundedButton(text='>', size_hint_x=None, width=dp(48))
        next_word_button.bind(on_release=self.load_next_word)
        nav_layout.add_widget(prev_word_button)
        nav_layout.add_widget(next_word_button)
        self.main_layout.add_widget(nav_layout)

        # Action buttons
        action_layout = GridLayout(cols=1, spacing=dp(8))
        show_translation_button = RoundedButton(text='Показать перевод', size_hint_y=None, height=dp(48))
        show_translation_button.bind(on_release=self.show_translation)
        show_mnemonic_button = RoundedButton(text='Показать подсказку', size_hint_y=None, height=dp(48))
        show_mnemonic_button.bind(on_release=self.show_mnemonic)
        learned_button = RoundedButton(text='Слово Изучено', size_hint_y=None, height=dp(48))
        learned_button.bind(on_release=self.mark_as_learned)
        action_layout.add_widget(show_translation_button)
        action_layout.add_widget(show_mnemonic_button)
        action_layout.add_widget(learned_button)
        self.main_layout.add_widget(action_layout)

        self.word_history = []
        self.current_word_index = -1
        self.load_random_word()

        # Bind swipe gestures
        self.word_layout.bind(on_touch_up=self.on_touch_up)

        return self.main_layout

    def on_touch_up(self, instance, touch):
        if touch.dx < -50:  # Swipe left
            self.load_next_word(None)
        elif touch.dx > 50:  # Swipe right
            self.load_previous_word(None)

    def set_theme_colors(self):
        if self.theme == 'light':
            self.bg_color = get_color_from_hex('#F2F2F7')
            self.text_color = get_color_from_hex('#000000')
            self.accent_color = get_color_from_hex('#007AFF')
        else:
            self.bg_color = get_color_from_hex('#1C1C1E')
            self.text_color = get_color_from_hex('#FFFFFF')
            self.accent_color = get_color_from_hex('#0A84FF')
        Window.clearcolor = self.bg_color

    def toggle_theme(self):
        self.theme = 'dark' if self.theme == 'light' else 'light'
        self.set_theme_colors()
        self.update_colors()
        anim = Animation(pos=(self.theme_button.x + dp(30), self.theme_button.y) if self.theme == 'dark' else (self.theme_button.x, self.theme_button.y), duration=0.2)
        anim.start(self.theme_button.switch)

    def update_colors(self):
        self.main_layout.canvas.before.clear()
        with self.main_layout.canvas.before:
            Color(*self.bg_color)
            RoundedRectangle(pos=self.main_layout.pos, size=self.main_layout.size)

        for child in self.main_layout.walk():
            if isinstance(child, Label):
                child.color = self.text_color
            elif isinstance(child, RoundedButton):
                child.rect_color.rgba = self.accent_color

    def load_random_word(self, instance=None):
        self.cursor.execute("SELECT * FROM words WHERE learned = 0 ORDER BY RANDOM() LIMIT 1")
        word = self.cursor.fetchone()
        if word:
            self.current_word = word
            self.word_label.text = str(word[1])
            self.transcription_label.text = str(word[4]).encode('utf-8').decode('utf-8')
            self.translation_label.text = str(word[2])
            self.mnemonic_label.text = f"Подсказка: {str(word[5])}"
            self.translation_label.opacity = 0
            self.mnemonic_label.opacity = 0
            self.word_history.append(word)
            self.current_word_index = len(self.word_history) - 1
            self.update_learned_status()
        else:
            self.word_label.text = "Все слова изучены!"
            self.transcription_label.text = ""
            self.translation_label.text = ""
            self.mnemonic_label.text = ""
            self.learned_status_label.text = ""

    def load_previous_word(self, instance):
        if self.current_word_index > 0:
            self.current_word_index -= 1
            self.current_word = self.word_history[self.current_word_index]
            self.update_word_display()

    def load_next_word(self, instance):
        if self.current_word_index < len(self.word_history) - 1:
            self.current_word_index += 1
            self.current_word = self.word_history[self.current_word_index]
            self.update_word_display()
        else:
            self.load_random_word()

    def update_word_display(self):
        self.word_label.text = str(self.current_word[1])
        self.transcription_label.text = str(self.current_word[4]).encode('utf-8').decode('utf-8')
        self.translation_label.text = str(self.current_word[2])
        self.mnemonic_label.text = f"Подсказка: {str(self.current_word[5])}"
        self.translation_label.opacity = 0
        self.mnemonic_label.opacity = 0
        self.update_learned_status()

    def update_learned_status(self):
        if self.current_word[3] == 1:
            self.learned_status_label.text = "Статус: Изучено"
            self.learned_status_label.color = get_color_from_hex('#34C759')
        else:
            self.learned_status_label.text = "Статус: Не изучено"
            self.learned_status_label.color = get_color_from_hex('#FF3B30')

    def show_translation(self, instance):
        self.translation_label.opacity = 1

    def show_mnemonic(self, instance):
        self.mnemonic_label.opacity = 1

    def mark_as_learned(self, instance):
        if hasattr(self, 'current_word'):
            self.cursor.execute("UPDATE words SET learned = 1 WHERE id = ?", (self.current_word[0],))
            self.conn.commit()
            self.current_word = list(self.current_word)
            self.current_word[3] = 1
            self.current_word = tuple(self.current_word)
            self.update_learned_status()
            self.word_history[self.current_word_index] = self.current_word
            self.load_next_word(None)

    def on_stop(self):
        self.conn.close()

if __name__ == '__main__':
    OwlishEnglishApp().run()

