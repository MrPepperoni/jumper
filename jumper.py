import pyglet
pyglet.options['audio'] = ('openal', 'pulse', 'directsound', 'silent')
import pyglet.media
from pyglet.window import key
from pyglet.window import mouse
from pyglet.gl import *
from enum import Enum
import librosa
import librosa.display
import random
import matplotlib.pyplot as plt
import numpy as np

class track:
    def plot(self):
        plt.figure(figsize=(8, 8))
        plt.plot(self.beats, 'ro', label='Onset strength')
        # plt.plot([x[1] for x in self.tempogram], label='tempogram')
        # plt.xticks([])
        # plt.legend(frameon=True)
        # plt.axis('tight')
        # librosa.display.specshow(self.tempogram, sr=self.sr, hop_length=self.hop_length, x_axis='time', y_axis='tempo')
        plt.show()
        if True:
            return
        plt.subplot(4, 1, 2)
        # We'll truncate the display to a narrower range of tempi
        librosa.display.specshow(self.tempogram, sr=self.sr, hop_length=self.hop_length,
                                 x_axis='time', y_axis='tempo')
        plt.axhline(self.tempo, color='w', linestyle='--', alpha=1,
                    label='Estimated tempo={:g}'.format(self.tempo))
        plt.legend(frameon=True, framealpha=0.75)
        plt.subplot(4, 1, 3)
        x = np.linspace(0, self.tempogram.shape[0] * float(self.hop_length) / self.sr,
                        num=self.tempogram.shape[0])
        plt.plot(x, np.mean(self.tempogram, axis=1), label='Mean local autocorrelation')
        plt.xlabel('Lag (seconds)')
        plt.axis('tight')
        plt.legend(frameon=True)
        plt.subplot(4,1,4)
        # We can also plot on a BPM axis
        freqs = librosa.tempo_frequencies(self.tempogram.shape[0], hop_length=self.hop_length, sr=self.sr)
        plt.semilogx(freqs[1:], np.mean(self.tempogram[1:], axis=1),
                     label='Mean local autocorrelation', basex=2)
        plt.axvline(self.tempo, color='black', linestyle='--', alpha=.8,
                    label='Estimated tempo={:g}'.format(self.tempo))
        plt.legend(frameon=True)
        plt.xlabel('BPM')
        plt.axis('tight')
        plt.grid()
        plt.tight_layout()
        plt.show()

    def __init__(self):
        audio_path = librosa.util.example_audio_file()
        # y is the waveform
        # we have it for harmonics, percussions
        # beats contain the timestamps of detected beats (could get frames)
        # should probably check the point plot
        self.y, self.sr = librosa.load(audio_path)
        self.hop_length = 512
        self.oenv = librosa.onset.onset_strength(y=self.y, sr=self.sr, hop_length=self.hop_length)
        self.y_harmonic = librosa.effects.harmonic(y=self.y)
        self.y_percussive = librosa.effects.percussive(y=self.y)
        self.tempo, self.beats = librosa.beat.beat_track(y=self.y, sr=self.sr, units='time', hop_length=self.hop_length)
        self.tempogram = librosa.feature.tempogram(y=self.y, sr=self.sr, hop_length=self.hop_length)
        self.sound = pyglet.media.load(audio_path)
        self.player = pyglet.media.Player()
        self.player.queue(self.sound)
        # self.plot()

        self.vertices =[None]*(len(self.oenv)*2)
        self.vertices[::2] = range(0,len(self.oenv))
        self.vertices[1::2] = [ x * 10 for x in self.oenv]
        self.vertices_gl = (GLfloat * len(self.vertices))(*self.vertices)
        glEnableClientState(GL_VERTEX_ARRAY)
        glVertexPointer(2, GL_FLOAT, 0, self.vertices_gl)
        print('loaded ' + audio_path + ' tempo: ' + str(self.tempo) + ' #beats: ' + str(len(self.beats))
                + ' #onset: ' + str(len(self.oenv)) + ' #tempogram: ' + str(len(self.tempogram)))
        print('#harmonic: ' + str(len(self.y_harmonic)))
        print('#percussive: ' + str(len(self.y_percussive)))
        print(str(self.y))
        for i in self.oenv:
            print('onset at ' + str(i))
        for i in self.beats:
            print('beat at ' + str(i))
        for i in self.tempogram:
            print('tempo at ' + str(i))

    def play(self):
        self.time = 0
        self.player.play()

    def end(self):
        self.player.stop()

    def draw(self):
        glClear(GL_COLOR_BUFFER_BIT)
        glLoadIdentity()
        glColor4f(1,1,1,1)
        glDrawArrays(GL_LINE_STRIP, 0, len(self.vertices) // 2)
        pass

    def update(self, t):
        self.time += t


class highscores:
    savefilename = 'hi.sav'
    maxscores = 10
    def __init__(self,g):
        self.g = g
        self.title = pyglet.text.Label('High Scores',
                font_name='Times New Roman',
                font_size=15,
                x=self.g.window.width/2,
                y=self.g.window.height - 25,
                anchor_x='center',
                anchor_y='center')
        self.scores = []
        self.labels = []
        self.load()

    def draw(self):
        self.title.draw()
        for x in self.labels:
            x.draw()

    def load(self):
        self.scores = []
        try:
            with open(self.__class__.savefilename, 'r') as f:
                self.scores = sorted([ int(x) for x in f ], reverse=True)
        except:
            pass
        self.update_labels()

    def update_labels(self):
        dy = 50
        self.labels.clear()
        for x in self.scores:
            self.labels.append(pyglet.text.Label(str(x),
                font_name='Times New Roman',
                font_size=10,
                x=self.g.window.width/2,
                y=self.g.window.height - dy,
                anchor_x='center',
                anchor_y='center'))
            dy += 15

    def add(self, score):
        mx = score - 1
        s = len(self.scores)
        if s > 0:
            mx = max(self.scores)

        self.scores.append(score)
        self.scores = sorted(self.scores, reverse=True)
        if s >= self.__class__.maxscores:
            self.scores.pop()
        self.save()
        self.update_labels()
        mn = min(self.scores)
        return mn <= score, mx < score

    def save(self):
        with open(self.__class__.savefilename, 'w') as f:
            for s in self.scores:
                print(str(s), file=f)


class menu:
    def draw(self):
        for x in self.labels:
            x.draw()

    def activate(self):
        self.actions[self.active](self)

    def start_game(self):
        print('starting game!')
        self.g.start()

    def show_highscores(self):
        print('showing highscores!')
        self.g.state = game.State.highscores

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
        self.entries = ['Play', 'High Scores', 'Quit']
        self.actions = [self.__class__.start_game, self.__class__.show_highscores, self.__class__.quit]
        self.active = 0
        self.labels = [pyglet.text.Label(x,
                    font_name='Times New Roman',
                    font_size=10,
                    x=self.g.window.width/2,
                    y=self.g.window.height/2,
                    anchor_x='center',
                    anchor_y='center') for x in self.entries]
        self.update_labels()

class gameover:
    def __init__(self, g):
        self.score = 0
        self.newhighscore = False
        self.newrecord = False
        self.g = g
        self.title = pyglet.text.Label('Game Over',
                font_name='Times New Roman',
                font_size=15,
                x=self.g.window.width/2,
                y=self.g.window.height - 155,
                anchor_x='center',
                anchor_y='center')
        self.high = pyglet.text.Label('You made the top 10!',
                font_name='Times New Roman',
                font_size=15,
                x=self.g.window.width/2,
                y=self.g.window.height/2,
                anchor_x='center',
                anchor_y='center')
        self.rec = pyglet.text.Label('Who\'s the best? Who\'s the best? YOU are the best!',
                font_name='Times New Roman',
                font_size=22,
                x=self.g.window.width/2,
                y=self.g.window.height/2,
                anchor_x='center',
                anchor_y='center')


    def over(self,score):
        self.score = score
        self.newhighscore, self.newrecord = self.g.highscores.add(score)

    def draw(self):
        self.title.draw()
        if self.newrecord:
            self.rec.draw()
        elif self.newhighscore:
            self.high.draw()
        pass

class game:
    class State(Enum):
        menu = 1
        ingame = 2
        gameover = 3
        highscores = 4

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
        self.highscores = highscores(self)
        self.gameover = gameover(self)
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
        if self.state == game.State.ingame:
            self.track.update(dt)
        pass

    def on_draw(self):
        pyglet.clock.tick()

        self.window.clear()
        if self.state == game.State.menu:
            self.menu.draw()
        elif self.state == game.State.highscores:
            self.highscores.draw()
        elif self.state == game.State.gameover:
            self.gameover.draw()
        elif self.state == game.State.ingame:
            self.track.draw()

        self.fps_display.draw()
        self.window.flip()

    def end_game(self, score):
        self.gameover.over(score)
        self.state = game.State.gameover

    def on_event(self,symbol,modifiers):
        print('key pressed: ' + str(symbol))
        if self.state == game.State.menu:
            self.menu.handle_keypress(symbol)
        if symbol == pyglet.window.key.ESCAPE:
            if self.state == game.State.ingame:
                self.end_game(random.randint(100,200))
            else:
                self.state = game.State.menu
            return pyglet.event.EVENT_HANDLED

    def on_mouse_press(self,x,y,button,modifiers):
        pass

    def run(self):
        pyglet.app.run()

    def start(self):
        self.newhighscore = False
        self.newrecord = False
        self.state = game.State.ingame
        self.track.play()

def main():
    g = game()
    g.run()

if __name__ == "__main__":
    main()

