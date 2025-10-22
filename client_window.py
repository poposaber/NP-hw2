import pygame
from client import Client
import pygame.freetype
import pygame.sysfont as sf

from ui_elements import InputBox, Button, Label



class ClientWindow:
    def __init__(self, width=800, height=600, title="Client Window"):
        self.client = Client()
        pygame.init()
        pygame.freetype.init()
        sf.initsysfonts()
        self.width = width
        self.height = height
        self.title = title
        self.screen = pygame.display.set_mode((self.width, self.height))
        pygame.display.set_caption(self.title)
        self.clock = pygame.time.Clock()
        self.running = False

        # font for UI elements
        self.input_font = pygame.freetype.SysFont("consolas", 18)
        self.label_font = pygame.freetype.SysFont("consolas", 15)
        self.caption_font = pygame.freetype.SysFont("consolas", 36)

        # UI elements
        self.account_input_box = InputBox(pygame.Rect(300, 250, 200, 32), self.input_font, on_submit=self.focus_on_pswd_box)
        self.password_input_box = InputBox(pygame.Rect(300, 325, 200, 32), self.input_font, on_submit=self.send_input)
        self.send_button = Button(pygame.Rect(360, 400, 80, 32), "Send", self.input_font, callback=self.send_input)
        self.login_label = Label((350, 150), "Login", self.caption_font)
        self.account_name_label = Label((300, 235), "Username", self.label_font)
        self.password_label = Label((300, 310), "Password", self.label_font)

    def send_input(self) -> None:
        print(f"Sending account: {self.account_input_box.text}")
        print(f"Sending password: {self.password_input_box.text}")
    
    def focus_on_pswd_box(self) -> None:
        self.account_input_box.active = False
        self.password_input_box.active = True

    def run(self):
        self.client.start()
        self.running = True

        while self.running:
            dt = self.clock.tick(60) / 1000.0  # Delta time in seconds
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                    self.client.close()
                self.password_input_box.handle_event(event)
                self.account_input_box.handle_event(event)
                self.send_button.handle_event(event)

            # update UI elements
            self.account_input_box.update(dt)
            self.password_input_box.update(dt)

            if self.client.fatal_error_event.is_set():
                self.running = False
                self.client.close()
            if self.client.shutdown_event.is_set():
                self.running = False

            self.screen.fill((10, 10, 10))  # Clear screen with dark gray

            # Draw UI elements
            self.account_input_box.draw(self.screen)
            self.password_input_box.draw(self.screen)
            self.send_button.draw(self.screen)
            self.login_label.draw(self.screen)
            self.account_name_label.draw(self.screen)
            self.password_label.draw(self.screen)

            pygame.display.flip()  # Update the display
            # self.clock.tick(60)  # Limit to 60 frames per second

        pygame.quit()