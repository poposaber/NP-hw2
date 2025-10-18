import pygame
import pygame.freetype

class Button:
    def __init__(self, rect, text, font, fg=(255,255,255), bg=(70,70,70), hover_bg=(100,100,100), callback=None):
        self.rect = pygame.Rect(rect)
        self.text = text
        self.font = font
        self.fg = fg
        self.bg = bg
        self.hover_bg = hover_bg
        self.callback = callback
        self.hover = False

    def handle_event(self, event):
        if event.type == pygame.MOUSEMOTION:
            self.hover = self.rect.collidepoint(event.pos)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                if self.callback:
                    self.callback()

    def draw(self, surf):
        color = self.hover_bg if self.hover else self.bg
        pygame.draw.rect(surf, color, self.rect, border_radius=6)
        text_surf = self.font.render(self.text, fgcolor=self.fg)[0]
        txt_rect = text_surf.get_rect(center=self.rect.center)
        surf.blit(text_surf, txt_rect)

class InputBox:
    def __init__(self, rect, font, text='', fg=(255,255,255), bg=(40,40,40), caret_color=(255,255,255), on_submit=None):
        self.rect = pygame.Rect(rect)
        self.font = font
        self.text = text
        self.fg = fg
        self.bg = bg
        self.caret_color = caret_color
        self.active = False
        self.cursor_visible = True
        self.cursor_timer = 0.0
        self.cursor_interval = 0.7
        self.on_submit = on_submit
        self.padding = 6
        # hover 與目前設定的系統游標（快取）
        self.hover = False
        self._cursor_state = None

    def handle_event(self, event):
        if event.type == pygame.MOUSEMOTION:
            self.hover = self.rect.collidepoint(event.pos)
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self.active = self.rect.collidepoint(event.pos)
        elif event.type == pygame.KEYDOWN and self.active:
            if event.key == pygame.K_RETURN:
                if self.on_submit:
                    self.on_submit()
            elif event.key == pygame.K_BACKSPACE:
                self.text = self.text[:-1]
            else:
                if event.unicode:
                    self.text += event.unicode

    def update(self, dt):
        if self.active:
            self.cursor_timer += dt
            if self.cursor_timer >= self.cursor_interval:
                self.cursor_timer -= self.cursor_interval
                self.cursor_visible = not self.cursor_visible
        else:
            self.cursor_visible = False
        # 每幀（或在 MOUSEMOTION 時）切換系統游標，避免重複設定
        desired = pygame.SYSTEM_CURSOR_IBEAM if self.hover else pygame.SYSTEM_CURSOR_ARROW
        if self._cursor_state != desired:
            try:
                pygame.mouse.set_cursor(pygame.cursors.Cursor(desired))
                self._cursor_state = desired
            except Exception:
                # 部分環境或 pygame 版本可能不支援系統游標，忽略錯誤
                self._cursor_state = None

    def draw(self, surf):
        pygame.draw.rect(surf, self.bg, self.rect, border_radius=6)
        txt_surf = self.font.render(self.text, fgcolor=self.fg)[0]
        surf.blit(txt_surf, (self.rect.x + self.padding, self.rect.y + (self.rect.h - txt_surf.get_height())//2))
        if self.active and self.cursor_visible:
            cursor_x = self.rect.x + self.padding + txt_surf.get_width() + 1
            cursor_y1 = self.rect.y + 8
            cursor_y2 = self.rect.y + self.rect.h - 8
            pygame.draw.line(surf, self.caret_color, (cursor_x, cursor_y1), (cursor_x, cursor_y2), 2)

class Label:
    def __init__(self, pos: tuple[float, float], text: str, font: pygame.freetype.Font, color=(255,255,255), align="topleft"):
        """
        pos: (x,y) 或 pygame.Rect 的位置依據 align
        text: 初始文字
        font: pygame.freetype.Font
        align: "topleft", "center", "midleft", etc.
        """
        self.pos = pos
        self.text = str(text)
        self.font = font
        self.color = color
        self.align = align

    def set_text(self, text):
        self.text = str(text)

    def draw(self, surf):
        text_surf, _ = self.font.render(self.text, fgcolor=self.color)
        rect = text_surf.get_rect()
        setattr(rect, self.align, self.pos)
        surf.blit(text_surf, rect)