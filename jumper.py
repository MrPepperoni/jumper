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
from scipy.misc import comb
import scipy
import os
import sys

def bernstein_poly(i, n, t):
    """
     The Bernstein polynomial of n, i as a function of t
    """

    return comb(n, i) * ( t**(n-i) ) * (1 - t)**i


def bezier_curve(xPoints, yPoints, nTimes=1000):
    """
       Given a set of control points, return the
       bezier curve defined by the control points.

       points should be a list of lists, or list of tuples
       such as [ [1,1], 
                 [2,3], 
                 [4,5], ..[Xn, Yn] ]
        nTimes is the number of time steps, defaults to 1000

        See http://processingjs.nihongoresources.com/bezierinfo/
    """

    nPoints = len(xPoints)

    t = np.linspace(0.0, 1.0, nTimes)

    polynomial_array = np.array([ bernstein_poly(i, nPoints-1, t) for i in range(0, nPoints)   ])

    xvals = np.dot(xPoints, polynomial_array)
    yvals = np.dot(yPoints, polynomial_array)

    return xvals, yvals


def curve(xv, yv, target):
    f = scipy.interpolate.interp1d(xv,yv,kind='cubic')
    minx = min(xv)
    maxx = max(xv)
    xr = [ max( min( maxx, (maxx - minx) * x / target + minx ), minx) for x in range(0, target) ]
    yr = [ f(x) for x in xr]
    return xr, yr
    # return bezier_curve(xv, yv, target)

class track:
    class Jump(Enum):
        floor = 1
        single = 2
        double = 3

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

    def gen_chroma(self):
        y = self.y
        sr = self.sr

        y_harm = librosa.effects.harmonic(y=y, margin=8)
        chroma_os_harm = librosa.feature.chroma_cqt(y=self.y_percussive, sr=sr, bins_per_octave=12*3)

        chroma_filter = np.minimum(chroma_os_harm,
                           librosa.decompose.nn_filter(chroma_os_harm,
                                                       aggregate=np.median,
                                                       metric='cosine'))

        self.chroma_smooth = scipy.ndimage.median_filter(chroma_filter, size=(1, 9))
        # sys.exit(0)

        D = librosa.stft(y)
        H, P = librosa.decompose.hpss(D)
        self.db = librosa.amplitude_to_db(D, ref=np.max)

    def gen_track(self):
        # self.gen_chroma()
        # tp = self.db.T

        #lst = librosa.onset.onset_strength(y=self.y_percussive, sr=self.sr, hop_length=self.hop_length)

        # print('t: %s n: %s' % (len(tp),len(tp[0])))

        # lst = [ max(1, 80 + max(tp[sample])) * (1 + np.argmax(tp[sample])) * max(1, 80 + np.average(tp[sample]))  for sample in range(0, len(tp)) ]
        # lst = [ (1 + np.argmax(tp[sample])) * (max(1, 80 + max(tp[sample])) * abs( np.sum(tp[sample])))  for sample in range(0, len(tp)) ]


        '''
        mi legyen a jo megoldas a palya genre?
        meg kene nezni a beateket, amikor beat van, akkor felmegyunk, amikor nincs, akkor le
        ez eddig zsirfeka
        es megnezzuk a beat utan az y maxot vagy a max decibelt, es meg azt raszorozzuk
        jo lesz?
        jo lesz.

        '''
        '''
        db chroma: frames
        y: samples
        '''

        # sys.exit(0)

        '''
        lst = None
        sampl = 20000
        while lst is None:
            try:
                lst = librosa.resample(self.y_percussive, self.sr, sampl)
            except:
                sampl *= 2

        self.tempo, self.beats = librosa.beat.beat_track(y=lst, sr=sampl, units='samples', hop_length=self.hop_length)
        print('beats: %i db: %i %i chroma: %i %i y: %i' %
                (len(self.beats),len(self.db),len(self.db[0]), len(self.chroma_smooth), len(self.chroma_smooth[0]), len(lst)))
        print(str(self.beats))
        '''
        numparts = 400
        lst = self.y
        lst = [ abs(x) * (ind in self.beats and 1 or 0) for ind, x in enumerate(lst) ]
        lst_harmonic = [ max(x) for x in np.array_split(lst,numparts) ]
        lst = self.y_percussive
        lst = [ abs(x) * (ind in self.beats and 1 or 0) for ind, x in enumerate(lst) ]
        lst_percussive = [ max(x) for x in np.array_split(lst,numparts) ]
        lst = [ x[0] > x[1] and -x[0] or x[1] for x in zip(lst_harmonic, lst_percussive) ]
        print(str(lst))
        vlen = len(lst)
        lst_max = max(max(lst),abs(min(lst)))
        mul = 30 / max(0.001, lst_max)

        xv = [ x * self.duration / vlen for x in range(0,vlen)]
        yv = [ x * mul for x in lst]

        target_points = vlen * 10
        xr, yr = curve(xv, yv, target_points)
        vlen = len(xr)
        self.vertices = [None]*(vlen*2)
        self.vertices[::2] = [ x * self.xmul for x in xr ]
        self.vertices[1::2] = yr

        #         self.vertices =[None]*(vlen*2)
        #         self.vertices[::2] = [ x * self.duration / vlen for x in range(0,vlen)]
        #         self.vertices[1::2] = [ abs(x) * mul for x in lst]

        self.vertices_gl = (GLfloat * len(self.vertices))(*self.vertices)

        self.lst = lst

    def __init__(self):
        audio_path = librosa.util.example_audio_file()
        # y is the waveform
        # we have it for harmonics, percussions
        # beats contain the timestamps of detected beats (could get frames)
        # should probably check the point plot
        self.window_length = 5  # seconds
        self.margin_l = 1.5
        self.margin_r = 0.0
        self.xmul = 5
        self.ball = 50
        self.ball_sp = 0
        self.ball_st = track.Jump.double

        self.y, self.sr = librosa.load(audio_path)
        self.hop_length = 512
        self.oenv = librosa.onset.onset_strength(y=self.y, sr=self.sr, hop_length=self.hop_length)
        self.duration = librosa.core.get_duration(y=self.y, sr=self.sr, hop_length=self.hop_length)
        self.y_harmonic, self.y_percussive = librosa.effects.hpss(y=self.y,margin=16.0)
        # librosa.output.write_wav(path='/tmp/harmonic.wav',y=self.y_harmonic,sr=self.sr)
        # librosa.output.write_wav(path='/tmp/percussive.wav',y=self.y_percussive,sr=self.sr)
        self.tempo, self.beats = librosa.beat.beat_track(y=self.y, sr=self.sr, units='samples', hop_length=self.hop_length)
        self.tempogram = librosa.feature.tempogram(y=self.y, sr=self.sr, hop_length=self.hop_length)
        self.sound = pyglet.media.load(audio_path)
        self.player = pyglet.media.Player()
        self.player.queue(self.sound)
        # self.plot()
        self.gen_track()

        glEnableClientState(GL_VERTEX_ARRAY)
        glVertexPointer(2, GL_FLOAT, 0, self.vertices_gl)
        print('loaded ' + audio_path + ' duration: ' + str(self.duration) + ' tempo: ' + str(self.tempo) + ' #beats: ' + str(len(self.beats))
                + ' #onset: ' + str(len(self.oenv)) + ' #tempogram: ' + str(len(self.tempogram)))
        print('#harmonic: ' + str(len(self.y_harmonic)))
        print('#percussive: ' + str(len(self.y_percussive)))
        print(str(self.y))

    def play(self):
        self.time = 0
        self.player.play()

    def end(self):
        self.player.stop()

    def get_amp(self,time):
        if time <= 0:
            return 0
        itime = int(time / self.duration * len(self.vertices)//2) * 2 + 1
        if itime >= len(self.vertices):
            return 0
        return max(0, min( self.vertices[itime] / 10, 1 ) )

    def get_h(self,time):
        itime = int(time / self.duration * len(self.vertices_gl)//2) * 2 + 1
        return self.vertices_gl[max(0,min(len(self.vertices_gl)-1,itime))]

    def draw(self):
        glClear(GL_COLOR_BUFFER_BIT)
        glMatrixMode(GL_PROJECTION)
        glPushMatrix()
        glLoadIdentity()
        glOrtho(-self.margin_l,self.window_length+self.margin_r,-50,50,-1,1)
        col = self.get_amp(self.time)
        glBegin(GL_QUADS)
        glColor4f(1,0,0,col)
        h = self.ball
        glVertex2f(-0.5,h-5)
        glColor4f(0,1,0,col)
        glVertex2f(0.5,h-5)
        glColor4f(0,0,1,col)
        glVertex2f(0.5,h+5)
        glColor4f(0,1,1,col)
        glVertex2f(-0.5,h+5)
        glEnd()
        glMatrixMode(GL_MODELVIEW)
        glPushMatrix()
        glLoadIdentity()

        glTranslatef(-self.time * self.xmul,0,0)    # self.time a teljes palya hossza, szoval a time vegere 0n kene lennunk ( kell meg egy margo )
        glColor4f(1,1,1,0)
        glDrawArrays(GL_LINE_STRIP, 0, len(self.vertices) // 2)

        glMatrixMode(GL_MODELVIEW)
        glPopMatrix()
        glMatrixMode(GL_PROJECTION)
        glPopMatrix()

        glMatrixMode(GL_MODELVIEW)
        pass


    def update(self, t):
        self.time += t
        self.ball_sp += 360 * t
        self.ball -= self.ball_sp * t
        h = self.get_h(self.time)
        if self.ball <= h or self.ball_st == track.Jump.floor:
            self.ball_st = track.Jump.floor
            self.ball = h
            self.ball_sp = 0

    def handle_keypress(self, symbol):
        if symbol == key.DOWN:
            pass
        elif symbol == key.UP:
            if self.ball_st != track.Jump.double:
                self.ball_sp = -120
                if self.ball_st == track.Jump.single:
                    self.ball_st = track.Jump.double
                else:
                    self.ball_st = track.Jump.single
        elif symbol == key.RETURN:
            pass


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
        elif self.state == game.State.ingame:
            self.track.handle_keypress(symbol)

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

