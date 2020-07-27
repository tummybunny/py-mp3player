"""
Husci MP3 Player
By Alexander Yanuar Koentjara
"""
import random
import pygame
import json
import os
from os import path

DEFAULT_LIBRARY = r"/home/alex/Music/library.mplib"
STATE_STOPPED = 0
STATE_PLAYING = 1
STATE_PAUSED = 2
LOOP_NO = 0
LOOP_ONE = 1
LOOP_ALL = 2


class Tracker:
    def __init__(self, storage):
        self.library = storage.library
        self.playlist = self.load(self.library['last'])
        self.shuffle = self.playlist['shuffle']
        self.loop = self.playlist['loop']
        self.state = STATE_STOPPED
        self.rnd = random.Random()
        self.prev = None

    def save(self):
        js_object = {
            "name": self.playlist["name"],
            "songs": self.playlist["songs"],
            "last": self.currentTrackPath(),
            "shuffle": self.shuffle,
            "loop": self.loop,
        }
        with open(self.library['last'], "w") as fp:
            json.dump(js_object, fp, indent=4)
            print(f"Saved to {self.library['last']}")

    def album(self):
        return self.playlist['name'] if self.playlist else None

    def currentTrackPath(self):
        return self.playlist['last'] if self.playlist else None

    def currentTrack(self):
        return path.basename(self.playlist['last']) if self.playlist else None

    def load(self, playlistFile):
        if path.isfile(playlistFile):
            with open(playlistFile) as fp:
                pl = json.load(fp)
                return pl
        else:
            return {
                "name": "New playlist",
                "songs": [],
                "last": None,
                "shuffle": True,
                "loop": LOOP_ALL
            }

    def setShuffle(self):
        self.shuffle = not self.shuffle
        self.save()

    def setLoop(self):
        if not self.loop:
            self.loop = 1
        else:
            self.loop = self.loop + 1
            if self.loop == 3:
                self.loop = LOOP_NO
        self.save()

    def monitor(self):
        if not pygame.mixer.music.get_busy() and self.currentTrackPath() and self.state == STATE_PLAYING:
            if self.loop == LOOP_ONE:
                self.play()
            elif not self.loop:
                self.state = STATE_STOPPED
            else:
                self.nextTrack()

    def next(self):
        if self.currentTrack():
            self.prev = self.currentTrackPath()
            self.nextTrack(auto_play=pygame.mixer.music.get_busy())

    def nextTrack(self, adder=1, auto_play=True):
        def searchIndex():
            for (i, s) in enumerate(self.playlist["songs"]):
                if s == self.currentTrackPath():
                    return i
            return -1

        if self.shuffle:
            if len(self.playlist["songs"])>1:
                originalIdx = searchIndex()
                while True:
                    idx = self.rnd.randint(0, len(self.playlist["songs"]) - 1)
                    if idx != originalIdx: 
                        break
                self.setCurrentTrack(self.playlist["songs"][idx], auto_play)
        else:
            idx = searchIndex()
            if idx >= 0:
                idx += adder
                if idx < 0:
                    idx = len(self.playlist["songs"]) - 1
                elif idx >= len(self.playlist["songs"]):
                    idx = 0
                self.setCurrentTrack(self.playlist["songs"][idx], auto_play)
            else:
                self.setCurrentTrack(None, auto_play)

    def setCurrentTrack(self, track, auto_play=True):
        if track:
            pygame.mixer.music.stop()
            self.playlist["last"] = track
            if auto_play:
                self.play()
            else:
                self.state = STATE_STOPPED

    def previous(self):
        if self.currentTrack():
            if self.prev:
                pygame.mixer.music.stop()
                self.setCurrentTrack(self.prev)
                self.prev = None
                self.play()
            elif not self.shuffle:
                self.nextTrack(adder=-1, auto_play=pygame.mixer.music.get_busy())
            else:
                # don't remember what previous is
                self.nextTrack(auto_play=pygame.mixer.music.get_busy())

    def stop(self):
        if pygame.mixer.music.get_busy() and self.currentTrackPath():
            pygame.mixer.music.stop()
            self.state = STATE_STOPPED
        elif self.state == STATE_PAUSED:
            pygame.mixer.music.stop()
            self.state = STATE_STOPPED

    def play(self):
        if self.state == STATE_PAUSED:
            pygame.mixer.music.unpause()
            self.state = STATE_PLAYING
        elif not pygame.mixer.music.get_busy() and self.currentTrackPath():
            pygame.mixer.music.load(self.currentTrackPath())
            pygame.mixer.music.play()
            self.state = STATE_PLAYING

    def pause(self):
        if self.state == STATE_PAUSED:
            pygame.mixer.music.unpause()
            self.state = STATE_PLAYING
        elif pygame.mixer.music.get_busy() and self.currentTrackPath():
            pygame.mixer.music.pause()
            self.state = STATE_PAUSED


class Lcd:

    POS_UNKNOWN = -1
    POS_FIXED = -2
    ROLLING_RATE = 2
    FONT_SIZE = 12

    def __init__(self, tracker, width):
        self.width = int(width * 0.95)
        self.height = Lcd.FONT_SIZE * 3 + 20
        self.offset = int((width - self.width) / 2)
        self.tracker = tracker
        self.bg = pygame.Surface((self.width, self.height)).convert()
        self.bigFont = pygame.font.SysFont('mono', Lcd.FONT_SIZE + 2, bold=True)
        self.font = pygame.font.SysFont('mono', Lcd.FONT_SIZE)
        self.smallFont = pygame.font.SysFont('mono', Lcd.FONT_SIZE - 1)
        self.song = tracker.currentTrack()
        self.pos = Lcd.POS_UNKNOWN
        self.rolling = 0

    def refreshTracker(self):
        self.song = self.tracker.currentTrack()
        self.rolling = 0
        self.pos = Lcd.POS_UNKNOWN

    def render(self):
        self.bg.fill((80, 60, 2))
        album = self.font.render(f"Album: {self.tracker.album()}", True, (255, 255, 120))
        self.bg.blit(album, (5, 5))

        # Render the shuffle and loop icon
        shuffle = "≈" if self.tracker.shuffle else " "
        loop = "∞" if self.tracker.loop == LOOP_ALL else "1" if self.tracker.loop == LOOP_ONE else " "
        text = self.bigFont.render(f"{shuffle}{loop} ", True, (255, 50, 50))
        self.bg.blit(text, (min(5 + album.get_size()[0] + 5, self.width - text.get_size()[0] - 5), 3))

        # Render song, if song is too long, make it rolling
        if self.song:
            longTitle = self.song + "   >>"
            if self.pos >= 0:
                self.rolling += 1
                if self.rolling % Lcd.ROLLING_RATE == 0:
                    self.rolling = 0
                    self.pos += 1
                    if self.pos >= len(longTitle):
                        self.pos = 0
            elif self.pos != Lcd.POS_FIXED:
                text = self.font.render(self.song, True, (0, 0, 0))
                self.pos = Lcd.POS_FIXED if text.get_size()[0] < self.width else 0

            title = self.song if self.pos == Lcd.POS_FIXED else \
                longTitle[self.pos:] + " " + longTitle[0:self.pos]
        else:
            title = "Song: --"

        text = self.font.render(title, True, (255, 255, 120))
        self.bg.blit(text, (5, Lcd.FONT_SIZE + 10))
        if pygame.mixer.music.get_busy() and self.tracker.currentTrack():
            pos = pygame.mixer.music.get_pos()
            state = "(paused) " if self.tracker.state == STATE_PAUSED else ""
            minutes = int(pos/60000)
            ss = (pos/1000) - (minutes*60)
            mm = f"{minutes}:" if minutes > 0 else ""
            oo = "0" if mm and ss < 10 else ""
            text = self.smallFont.render(f"{state}{mm}{oo}{ss:.2f}s", True, (180, 180, 180))
            self.bg.blit(text, (self.width - text.get_size()[0] - 5, Lcd.FONT_SIZE * 2 + 15))
        return self.bg, self.offset, self.offset


class Mp3Player:
    def __init__(self, storage, width=200, height=110):
        info = pygame.display.Info()
        self.storage = storage
        self.width = width
        self.height = height
        self.tracker = Tracker(storage)
        self.screenSize = (info.current_w, info.current_h)
        self.displayPosition = storage.win_position
        self.setPosition(*self.displayPosition)
        self.screen = pygame.display.set_mode((self.width, self.height), flags=pygame.NOFRAME)
        pygame.display.set_caption("MP3 Player")
        self.lcd = Lcd(self.tracker, width)
        self.font = pygame.font.SysFont('mono', 10, bold=True)
        self.buttons = []
        self.buttonRects = {}

    def setPosition(self, x, y):
        os.environ['SDL_VIDEO_WINDOW_POS'] = '%d,%d' % (x, y)
        pygame.display.set_mode((self.width-1, self.height), flags=pygame.NOFRAME)
        pygame.display.set_mode((self.width, self.height), flags=pygame.NOFRAME)
        self.displayPosition = (x, y)
        self.storage.win_position = (x, y)
        self.storage.save()

    def renderCaption(self, bg):
        bg.fill((0, 128, 64), (0, 0, self.width, 15))
        caption = self.font.render("Husci MP3 Player", True, (0, 255, 0))
        bg.blit(caption, (2, 2))
        bg.fill((0, 60, 0), (self.width - 13, 3, 10, 10))
        pygame.draw.line(bg, (0, 255, 0), (self.width - 12, 4), (self.width - 5, 11))
        pygame.draw.line(bg, (0, 255, 0), (self.width - 5, 4), (self.width - 12, 11))
        return self.width - 13, 3, self.width - 3, 13

    def renderButtons(self, bg, offsetX, offsetY):
        if not self.buttonRects:
            key = ["prev", "play", "pause", "stop", "next", "shuffle", "loop"]
            txt = ["|<", " > ", "||", " ■ ", ">|", " Shf ", " Loop "]
            lastX = offsetX
            for (i, k) in zip(txt, key):
                txt = self.font.render(i, True, (0, 255, 0))
                x, y = txt.get_size()
                but = pygame.Surface((x+4, y+4)).convert()
                but.fill((0, 128, 64))
                but.blit(txt, (2, 2))
                self.buttons.append((but, lastX))
                self.buttonRects[k] = (lastX, offsetY, lastX + x + 4, offsetY + y + 4)
                lastX += x + 8

        for (but, x) in self.buttons:
            bg.blit(but, (x, offsetY))

    def run(self):
        def pointInside(x1, y1, x2, y2):
            mousex, mousey = pygame.mouse.get_pos()
            return x1 <= mousex <= x2 and y1 <= mousey <= y2

        bg = pygame.Surface(self.screen.get_size()).convert()
        clock = pygame.time.Clock()
        running = True

        while running:
            bg.fill((254, 247, 192))
            closeRect = self.renderCaption(bg)

            lcd, x, y = self.lcd.render()
            bg.blit(lcd, (x, y + 20))
            lcdHeight = lcd.get_size()[1]

            self.renderButtons(bg, 5, y + 20 + lcdHeight + 5)
            self.screen.blit(bg, (0, 0))

            oldTrack = self.tracker.currentTrack()
            self.tracker.monitor()
            if self.tracker.currentTrack() != oldTrack:
                self.lcd.refreshTracker()

            clock.tick(10)

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if pointInside(*closeRect):
                        running = False
                    if pointInside(*self.buttonRects["prev"]):
                        self.tracker.previous()
                        self.lcd.refreshTracker()
                    if pointInside(*self.buttonRects["play"]):
                        self.tracker.play()
                        self.lcd.refreshTracker()
                    if pointInside(*self.buttonRects["pause"]):
                        self.tracker.pause()
                        self.lcd.refreshTracker()
                    if pointInside(*self.buttonRects["stop"]):
                        self.tracker.stop()
                        self.lcd.refreshTracker()
                    if pointInside(*self.buttonRects["next"]):
                        self.tracker.next()
                        self.lcd.refreshTracker()
                    if pointInside(*self.buttonRects["shuffle"]):
                        self.tracker.setShuffle()
                        self.lcd.refreshTracker()
                    if pointInside(*self.buttonRects["loop"]):
                        self.tracker.setLoop()
                        self.lcd.refreshTracker()
                elif event.type == pygame.KEYDOWN:
                    if pygame.key.get_mods() & pygame.KMOD_RCTRL:
                        if event.key == pygame.K_q:
                            running = False
                        if event.key == pygame.K_UP or event.key == pygame.K_KP8:
                            self.setPosition(self.displayPosition[0], self.displayPosition[1] - 10)
                        if event.key == pygame.K_RIGHT or event.key == pygame.K_KP6:
                            self.setPosition(self.displayPosition[0] + 10, self.displayPosition[1])
                        if event.key == pygame.K_DOWN or event.key == pygame.K_KP2:
                            self.setPosition(self.displayPosition[0], self.displayPosition[1] + 10)
                        if event.key == pygame.K_LEFT or event.key == pygame.K_KP4:
                            self.setPosition(self.displayPosition[0] - 10, self.displayPosition[1])
                        if event.key == pygame.K_HOME or event.key == pygame.K_KP7:
                            self.setPosition(0, 0)
                        if event.key == pygame.K_PAGEUP or event.key == pygame.K_KP9:
                            self.setPosition(self.screenSize[0]-self.width, 0)
                        if event.key == pygame.K_END or event.key == pygame.K_KP1:
                            self.setPosition(0, self.screenSize[1]-self.height)
                        if event.key == pygame.K_PAGEDOWN or event.key == pygame.K_KP3:
                            self.setPosition(self.screenSize[0]-self.width, self.screenSize[1]-self.height)

            pygame.display.flip()

        self.tracker.save()
        self.storage.save()


class Storage:
    def __init__(self, library_file):
        self.library_file = library_file
        if path.isfile(library_file):
            with open(library_file) as fp:
                self.library = json.load(fp)
        else:
            self.library = {
                "name": "Default",
                "ui": {
                    "x": 0,
                    "y": 0,
                 },
                "playlists": ["library.mplib"],
                "last": "library.mplib"
            }
        self.win_position = (self.library["ui"]["x"], self.library["ui"]["y"])

    def save(self):
        js_object = {
            "name": self.library["name"],
            "ver": 1,
            "ui": {
                "x": self.win_position[0],
                "y": self.win_position[1],
            },
            "playlists": self.library["playlists"],
            "last": self.library["last"]
        }
        with open(self.library_file, "w") as fp:
            json.dump(js_object, fp, indent=4)
            print(f"Saved to {self.library_file}")


def main():
    pygame.init()
    pygame.mixer.pre_init(44100, -16, 2, 2048)
    pygame.mixer.init()
    storage = Storage(DEFAULT_LIBRARY)
    player = Mp3Player(storage)
    player.run()
    pygame.quit()


if __name__ == "__main__":
    main()
