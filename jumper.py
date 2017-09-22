import pyglet
pyglet.options['audio'] = ('openal', 'pulse', 'directsound', 'silent')
import pyglet.media
from pyglet.window import key
from pyglet.window import mouse
from pyglet.gl import *
from enum import Enum
import librosa

class track:
    def __init__(self):
        audio_path = librosa.util.example_audio_file()
        self.y, self.sr = librosa.load(audio_path)
        self.tempo, self.beats = librosa.beat.beat_track(y=self.y, sr=self.sr)
        self.sound = pyglet.media.load(audio_path)
        print('loaded ' + audio_path + ' tempo: ' + str(self.tempo) + ' #beats: ' + str(len(self.beats)))

    def play(self):
        self.sound.play()

class menu:
    def draw(self):
        for x in self.labels:
            x.draw()

    def activate(self):
        self.actions[self.active](self)

    def start_game(self):
        print('starting game!')
        self.g.start()

    def show_controls(self):
        print('showing controls!')

    def show_highscores(self):
        print('showing highscores!')

    def quit(self):
        pyglet.app.exit()

    def move_focus(self, direction):
        self.active += direction
        if self.active < 0:
            self.active = len(self.actions) - 1
        if self.active >=len(self.actions):
            self.active = 0
        print('active entry: ' + str(self.active) + ' ' + self.entries[self.active])
        self.update_labels()
        self.g.window.invalid = True

    def label_height(self):
        return self.g.window.height/2/len(self.entries)
    
    def update_labels(self):
        for i in range(0, len(self.entries)):
            text = self.entries[i]
            lh = self.label_height()

            dy = (i - self.active) * lh

            font_size = lh
            if i != self.active:
                font_size *= 0.5

            lab = self.labels[i]
            lab.begin_update()
            lab.font_size=font_size
            lab.x=self.g.window.width/2
            lab.y=self.g.window.height/2-dy
            lab.end_update()

    def handle_keypress(self, symbol):
        if symbol == key.DOWN:
            self.move_focus(1)
        elif symbol == key.UP:
            self.move_focus(-1)
        elif symbol == key.RETURN:
            self.activate()

    def __init__(self,g):
        self.g = g
        self.entries = ['Play', 'Controls', 'High Scores', 'Quit']
        self.actions = [self.__class__.start_game, self.__class__.show_controls, self.__class__.show_highscores, self.__class__.quit]
        self.active = 0
        self.labels = [pyglet.text.Label(x,
                    font_name='Monospace',
                    font_size=10,
                    x=self.g.window.width/2,
                    y=self.g.window.height/2,
                    anchor_x='center',
                    anchor_y='center') for x in self.entries]
        self.update_labels()

class game:
    class State(Enum):
        menu = 1
        ingame = 2
        gameover = 3

    def __init__(self):
        config = pyglet.gl.Config(double_buffer=True)
        self.window = pyglet.window.Window(config=config,vsync=False)    # fullscreen = True
        self.window.push_handlers(pyglet.window.event.WindowEventLogger())
        pyglet.clock.schedule_interval(self.update, 1.0/128.0)
        pyglet.clock.set_fps_limit(128)
        # self.window.set_exclusive_mouse()
        self.fps_display = pyglet.clock.ClockDisplay()
        self.state = game.State.menu
        self.menu = menu(self)
        self.track = track()
        @self.window.event
        def on_draw():
            return self.on_draw()
        @self.window.event
        def on_key_press(s,m):
            return self.on_event(s,m)
        @self.window.event
        def on_mouse_press(x,y,button,modifiers):
            return self.on_mouse_press(x,y,button,modifiers)

    def update(self, dt):
        pass

    def on_draw(self):
        pyglet.clock.tick()

        self.window.clear()
        if self.state == game.State.menu:
            self.menu.draw()
        self.fps_display.draw()
        self.window.flip()

    def on_event(self,symbol,modifiers):
        print('key pressed: ' + str(symbol))
        if self.state == game.State.menu:
            self.menu.handle_keypress(symbol)
        if symbol == pyglet.window.key.ESCAPE:
            self.state = game.State.menu
            return pyglet.event.EVENT_HANDLED

    def on_mouse_press(self,x,y,button,modifiers):
        pass

    def run(self):
        pyglet.app.run()

    def start(self):
        self.state = game.State.ingame
        self.track.play()

def main():
    g = game()
    g.run()

if __name__ == "__main__":
    main()

