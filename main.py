from kivy.app import App
from kivymd.app import MDApp
from kivymd.uix.screen import MDScreen
from kivymd.uix.button import MDRaisedButton
from kivymd.uix.label import MDLabel
from kivy.core.window import Window
from kivy.metrics import dp
import sqlite3
from kivy.core.text import LabelBase
from kivy.animation import Animation
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.scrollview import MDScrollView
from kivy.properties import StringProperty, ObjectProperty
from kivymd.uix.toolbar import MDTopAppBar
from kivy.clock import Clock


LabelBase.register(name='PhoneticFont', fn_regular='Fonts/phonetic.ttf')
LabelBase.register(name='Vintage', fn_regular='Fonts/Vintage.otf')

class MainScreen(MDScreen):
    pass

class OwlishEnglishApp(MDApp):
    current_word_id = ObjectProperty(None)
    is_word_learned = ObjectProperty(False)
    is_review_mode = ObjectProperty(False)

    def switch_mode(self):
        self.is_review_mode = not self.is_review_mode
        if self.is_review_mode:
            self.load_random_learned_word()
        else:
            self.load_random_word()
        self.update_toolbar()

    def update_toolbar(self):
        if self.root:
            self.root.ids.toolbar.title = "Повторение" if self.is_review_mode else "Изучение"
            self.root.ids.toolbar.left_action_items = [
                ["book-refresh", lambda x: self.switch_mode(), "Изучение" if self.is_review_mode else "Повторение"]
            ]
    def switch_to_review_mode(self):
        self.is_review_mode = True
        self.load_random_learned_word()

    def switch_to_normal_mode(self):
        self.is_review_mode = False
        self.load_random_word()

    def load_random_learned_word(self):
        self.cursor.execute("SELECT * FROM words WHERE learned = 1 ORDER BY RANDOM() LIMIT 1")
        word = self.cursor.fetchone()
        if word:
            self.current_word_id = word[0]
            self.display_word(word)
        else:
            self.root.ids.word_label.text = "Нет изученных слов"

    def mark_as_unlearned(self):
        if self.current_word_id is not None:
            self.cursor.execute("UPDATE words SET learned = 0 WHERE id = ?", (self.current_word_id,))
            self.conn.commit()
            self.is_word_learned = False
            self.root.ids.learned_status.text = "Не изучено"
            Clock.schedule_once(lambda dt: self.load_random_learned_word(), 1)
        else:
            print("No word selected")

    def build(self):
        self.theme_cls.primary_palette = "Blue"
        self.theme_cls.theme_style = "Light"
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
        # self.load_random_word()  # Загрузим случайное слово при запуске
        Clock.schedule_once(self.load_random_word, 0)

        return MainScreen()

    def toggle_theme(self):
        self.theme_cls.theme_style = "Dark" if self.theme_cls.theme_style == "Light" else "Light"
        self.theme_mode = self.theme_cls.theme_style

    def load_random_word(self,*args):
        self.cursor.execute("SELECT * FROM words WHERE learned = 0 ORDER BY RANDOM() LIMIT 1")
        word = self.cursor.fetchone()
        if word:
            self.current_word_id = word[0]  # Сохраняем ID текущего слова
            self.display_word(word)
        else:
            self.display_no_words()

    def load_next_word(self):
        if self.current_word_id is not None:
            self.cursor.execute("SELECT * FROM words WHERE id > ? AND learned = 0 ORDER BY id ASC LIMIT 1", (self.current_word_id,))
            word = self.cursor.fetchone()
            if word:
                self.current_word_id = word[0]
                self.display_word(word)
            else:
                # Если следующего слова нет, загружаем первое неизученное слово
                self.cursor.execute("SELECT * FROM words WHERE learned = 0 ORDER BY id ASC LIMIT 1")
                word = self.cursor.fetchone()
                if word:
                    self.current_word_id = word[0]
                    self.display_word(word)
                else:
                    self.display_no_words()

    def load_previous_word(self):
        if self.current_word_id is not None:
            self.cursor.execute("SELECT * FROM words WHERE id < ? AND learned = 0 ORDER BY id DESC LIMIT 1", (self.current_word_id,))
            word = self.cursor.fetchone()
            if word:
                self.current_word_id = word[0]
                self.display_word(word)
            else:
                # Если предыдущего слова нет, загружаем последнее неизученное слово
                self.cursor.execute("SELECT * FROM words WHERE learned = 0 ORDER BY id DESC LIMIT 1")
                word = self.cursor.fetchone()
                if word:
                    self.current_word_id = word[0]
                    self.display_word(word)
                else:
                    self.display_no_words()

    def display_word(self, word):
        if self.root is None:
            print("Root is not initialized yet. Scheduling display update.")
            Clock.schedule_once(lambda dt: self.display_word(word), 0)
            return

        self.root.ids.word_label.text = str(word[1])
        self.root.ids.transcription_label.text = str(word[4])
        self.root.ids.translation_label.text = str(word[2])
        self.root.ids.mnemonic_label.text = f"Подсказка: {str(word[5])}"
        self.root.ids.translation_label.opacity = 0
        self.root.ids.mnemonic_label.opacity = 0
        self.is_word_learned = bool(word[3])
        self.root.ids.learned_status.text = "Изучено" if self.is_word_learned else "Не изучено"

        # Показываем/скрываем кнопки в зависимости от режима
        self.root.ids.mark_learned_button.opacity = 0 if self.is_review_mode else 1
        self.root.ids.mark_unlearned_button.opacity = 1 if self.is_review_mode else 0

    def display_no_words(self):
        self.root.ids.word_label.text = "Все слова изучены!"
        self.root.ids.transcription_label.text = ""
        self.root.ids.translation_label.text = ""
        self.root.ids.mnemonic_label.text = ""
        self.current_word_id = None

    def show_translation(self):
        self.root.ids.translation_label.opacity = 1

    def show_mnemonic(self):
        self.root.ids.mnemonic_label.opacity = 1

    def mark_as_learned(self):
        if self.current_word_id is not None:
            self.cursor.execute("UPDATE words SET learned = 1 WHERE id = ?", (self.current_word_id,))
            self.conn.commit()
            self.is_word_learned = True
            self.root.ids.learned_status.text = "Изучено"
            Clock.schedule_once(lambda dt: self.load_random_word(), 1)  # Загрузить новое слово через 1 секунду
        else:
            print("No word selected")

    def on_stop(self):
        self.conn.close()

if __name__ == '__main__':
    OwlishEnglishApp().run()



