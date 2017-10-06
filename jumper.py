import pyglet
pyglet.options['audio'] = ('openal', 'pulse', 'directsound', 'silent')
import pyglet.media
from pyglet.window import key
from pyglet.window import mouse
from pyglet.gl import *
from enum import Enum
import librosa
import random
import numpy as np
import scipy
from pyglet2d import Shape
import random

point_penalty = 5
point_reward = 1
bomb_size = 0.3
coin_size = 0.05
slide_time_max = 0.8
slide_ball_speed = 0.1
ball_accel = 20
jump_speed = 7
drop_speed = 5.2
beat_coin_delay = 0.02
beat_bomb_delay = 0.1
verbose_fs = 12
info_fs = 14
important_fs = 18
track_line_width = 5

def print_loading(window):
    l = pyglet.text.Label('Loading...',
        font_name='Times New Roman',
        font_size=verbose_fs,
        x=window.width/2,
        y=window.height/2,
        anchor_x='center',
        anchor_y='center')
    window.clear()
    l.draw()
    glFinish()
    window.flip()
    window.clear()
    l.draw()
    glFinish()
    window.flip()

def curve(xv, yv, target):
    f = scipy.interpolate.interp1d(xv,yv,kind='cubic')
    minx = min(xv)
    maxx = max(xv)
    xr = [ max( min( maxx, (maxx - minx) * x / target + minx ), minx) for x in range(0, target) ]
    yr = [ f(x) for x in xr]
    return xr, yr

class track:
    class Jump(Enum):
        floor = 1
        single = 2
        double = 3

    class Slide(Enum):
        no = 1
        during = 2
        done = 3

    def gen_track(self):
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
        mul = 1 / max(0.001, lst_max)

        xv = [ x * self.duration / vlen for x in range(0,vlen)]
        yv = [ x * mul for x in lst]

        target_points = vlen * 10
        xr, yr = curve(xv, yv, target_points)
        # xr, yr = xv, yv
        vlen = len(xr)
        self.vertices = [None]*(vlen*2)
        self.vertices[::2] = [ x * self.xmul for x in xr ]
        self.vertices[1::2] = yr

        self.vertices_gl = (GLfloat * len(self.vertices))(*self.vertices)
        self.lst = lst

    def __init__(self, g):
        self.g = g
        self.loaded = False

    def update_score(self):
        self.score = pyglet.text.Label('Score: %i' % self.points,
                font_name='Times New Roman',
                font_size=important_fs,
                x=self.g.window.width / 2,
                y=self.g.window.height - 20,
                anchor_x='center',
                anchor_y='center')

    def load(self):
        try:
            self.player.pause()
            self.player.seek(0)
        except:
            pass

        if self.loaded:
            for c in self.coins:
                c.enable(True)
            for b in self.bombs:
                b.enable(True)
            return

        print_loading(self.g.window)
        self.points = 0
        audio_path = librosa.util.example_audio_file()
        random.seed(audio_path)
        # y is the waveform
        # we have it for harmonics, percussions
        # beats contain the timestamps of detected beats (could get frames)
        # should probably check the point plot
        self.window_length = 5  # seconds
        self.margin_l = 1.5
        self.margin_r = 0.0
        self.xmul = 5
        self.ball_y = 2
        self.ball = Shape.circle([0,self.ball_y],0.1)
        self.ball_sp = 0
        self.ball_st = track.Jump.double
        self.slide = track.Slide.no
        self.slide_time = 0
        self.time = 0

        self.y, self.sr = librosa.load(audio_path)
        self.hop_length = 512
        self.duration = librosa.core.get_duration(y=self.y, sr=self.sr, hop_length=self.hop_length)
        self.y_harmonic, self.y_percussive = librosa.effects.hpss(y=self.y,margin=16.0)
        self.tempo, self.beats = librosa.beat.beat_track(y=self.y, sr=self.sr, units='samples', hop_length=self.hop_length)
        self.sound = pyglet.media.load(audio_path)
        self.player = pyglet.media.Player()
        self.player.queue(self.sound)
        self.gen_track()
        self.update_score()
        self.coins = []
        self.bombs = []
        for time in librosa.core.samples_to_time(self.beats):
            roll = random.randint(0,6)
            if roll > 2:
                t = time + beat_coin_delay
                self.coins.append(Shape.circle([t * self.xmul, self.get_h(t) + random.uniform(0.3,1.2)],coin_size))
            elif roll > 0:
                t = time + beat_bomb_delay
                self.bombs.append(Shape.circle([t * self.xmul, self.get_h(t) + random.uniform(0.5,1.5)],bomb_size,color=[128,0,0]))

        glEnableClientState(GL_VERTEX_ARRAY)
        glVertexPointer(2, GL_FLOAT, 0, self.vertices_gl)
        self.loaded = True

    def play(self):
        self.time = -1
        self.player.seek(0)
        # az update fogja a valosagban elinditani

    def end(self):
        try:
            self.player.pause()
        except:
            pass
        self.g.end_game(self.points)
        self.points = 0
        self.time = -1

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

    # ezt okosabban is lehetne, tudjuk, hogy melyk beatek jatszhatnak egyaltalan minden egyes idopontban
    def is_visible(self, circle):
        return circle.enabled and circle.center[0] + circle.radius >= self.time * self.xmul - self.margin_l and circle.center[0] - circle.radius < self.time * self.xmul + self.window_length + self.margin_r

    def draw(self):
        glClear(GL_COLOR_BUFFER_BIT)
        self.score.draw()
        glMatrixMode(GL_PROJECTION)
        glPushMatrix()
        glLoadIdentity()
        scale = self.g.window.height / self.g.window.width
        w = self.margin_l + self.margin_r + self.window_length
        glOrtho(-self.margin_l,self.window_length+self.margin_r,int(-w * scale / 2),int(w * scale / 2),-1,1)
        glMatrixMode(GL_MODELVIEW)
        glPushMatrix()
        glLoadIdentity()

        col = self.get_amp(self.time)

        glTranslatef(-self.time * self.xmul,0,0)    # self.time a teljes palya hossza, szoval a time vegere 0n kene lennunk ( kell meg egy margo )
        self.ball.draw()
        glColor4f(1,1,1,0)
        glLineWidth(track_line_width)
        glEnable(GL_LINE_SMOOTH);
        glHint(GL_LINE_SMOOTH_HINT, GL_NICEST);
        glDrawArrays(GL_LINE_STRIP, 0, len(self.vertices) // 2)
        for c in self.coins:
            if self.is_visible(c):
                c.draw()
        for c in self.bombs:
            if self.is_visible(c):
                c.draw()
        glMatrixMode(GL_MODELVIEW)
        glPopMatrix()
        glMatrixMode(GL_PROJECTION)
        glPopMatrix()
        glMatrixMode(GL_MODELVIEW)


    def update(self, t):
        # kozvetlen betoltes utan kapunk egy mocsoknagy dt-t, es a palya kozepere ugrunk. not fun.
        if self.time < -0.5:
            self.time = 0
            self.player.play()
            return

        self.time += t
        self.ball_sp += ball_accel * t
        if self.slide == track.Slide.during:
            self.slide_time += t
            if self.slide_time < slide_time_max and self.ball_st != track.Jump.floor:
                self.ball_sp = slide_ball_speed
        self.ball_y -= self.ball_sp * t
        h = self.get_h(self.time)
        if self.ball_y - self.ball.radius <= h or self.ball_st == track.Jump.floor:
            self.ball_st = track.Jump.floor
            self.slide = track.Slide.no
            self.ball_y = h + self.ball.radius
            self.ball_sp = 0

        self.ball.center = [self.time * self.xmul, self.ball_y]
        self.ball.enable(True)

        opoints = self.points

        for c in self.coins:
            if self.is_visible(c):
                if self.ball.overlaps(c):
                    c.enable(False)
                    self.points += point_reward

        for c in self.bombs:
            if self.is_visible(c):
                if self.ball.overlaps(c):
                    c.enable(False)
                    self.points -= point_penalty
                    if self.points < 0:
                        self.points = 0

        if opoints != self.points:
            self.update_score()

        if self.time >= self.duration:
            self.end()

    def handle_keypress(self, symbol):
        if symbol in [key.UP, key.W]:
            if self.ball_st != track.Jump.double:
                self.ball_sp = -jump_speed
                if self.ball_st == track.Jump.single:
                    self.ball_st = track.Jump.double
                else:
                    self.ball_st = track.Jump.single
        elif symbol in [ key.DOWN, key.S ]:
            self.ball_sp += drop_speed
            self.ball_st = track.Jump.double
        elif symbol in [ key.SPACE, key.RIGHT, key.D ]:
            if self.slide == track.Slide.no:
                self.slide = track.Slide.during
                self.slide_time = 0

    def handle_keyrelease(self, symbol):
        if symbol in [ key.SPACE, key.RIGHT, key.D ]:
            if self.slide != track.Slide.no:
                self.slide = track.Slide.done


class highscores:
    savefilename = 'hi.sav'
    maxscores = 10
    def __init__(self,g):
        self.g = g
        self.title = pyglet.text.Label('High Scores',
                font_name='Times New Roman',
                font_size=important_fs,
                x=self.g.window.width/2,
                y=self.g.window.height - 3 * important_fs,
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
        dy = 5 * important_fs
        self.labels.clear()
        for x in self.scores:
            self.labels.append(pyglet.text.Label(str(x),
                font_name='Times New Roman',
                font_size=info_fs,
                x=self.g.window.width/2,
                y=self.g.window.height - dy,
                anchor_x='center',
                anchor_y='center'))
            dy += int(info_fs * 1.5)

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
                    font_size=verbose_fs,
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
                font_size=info_fs,
                x=self.g.window.width/2,
                y=self.g.window.height - 155,
                anchor_x='center',
                anchor_y='center')
        self.high = pyglet.text.Label('You made the top 10!',
                font_name='Times New Roman',
                font_size=important_fs,
                x=self.g.window.width/2,
                y=self.g.window.height/2,
                anchor_x='center',
                anchor_y='center')
        self.rec = pyglet.text.Label('Who\'s the best? Who\'s the best? YOU are the best!',
                font_name='Times New Roman',
                font_size=important_fs,
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
        config = pyglet.gl.Config(double_buffer=True, sample_buffers=1, samples=4)
        self.window = pyglet.window.Window(config=config,vsync=False)    # fullscreen = True
        self.window.push_handlers(pyglet.window.event.WindowEventLogger())
        pyglet.clock.schedule_interval(self.update, 1.0/128.0)
        pyglet.clock.set_fps_limit(128)
        # self.window.set_exclusive_mouse()
        self.fps_display = pyglet.clock.ClockDisplay()
        self.state = game.State.menu
        self.menu = menu(self)
        self.track = track(self)
        self.highscores = highscores(self)
        self.gameover = gameover(self)
        @self.window.event
        def on_draw():
            return self.on_draw()
        @self.window.event
        def on_key_press(s,m):
            return self.on_key_press(s,m)
        @self.window.event
        def on_mouse_press(x,y,button,modifiers):
            return self.on_mouse_press(x,y,button,modifiers)
        @self.window.event
        def on_key_release(s,m):
            return self.on_key_release(s,m)
 
    def update(self, dt):
        if self.state == game.State.ingame:
            self.track.update(dt)
            self.window.invalid = True
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

    def end_game(self, score):
        if score >= 0:
            self.gameover.over(score)
        self.state = game.State.gameover

    def on_key_release(self,symbol,modifiers):
        print('key released: ' + str(symbol))
        if self.state == game.State.ingame:
            self.track.handle_keyrelease(symbol)
        return pyglet.event.EVENT_HANDLED

    def on_key_press(self,symbol,modifiers):
        print('key pressed: ' + str(symbol))
        if self.state == game.State.menu:
            self.menu.handle_keypress(symbol)
        elif self.state == game.State.ingame:
            self.track.handle_keypress(symbol)

        if symbol == pyglet.window.key.RETURN:
            # for some reason auto-leaves high scores on entering it...
            #if self.state == game.State.highscores:
            #    self.state = game.State.menu
            #    return pyglet.event.EVENT_HANDLED
            if self.state == game.State.gameover:
                self.state = game.State.highscores
                return pyglet.event.EVENT_HANDLED

        if symbol == pyglet.window.key.ESCAPE:
            if self.state == game.State.ingame:
                self.end_game(-1)
            elif self.state == game.State.menu:
                pyglet.app.exit()
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
        self.track.load()
        self.track.play()

def main():
    g = game()
    g.run()

if __name__ == "__main__":
    main()

