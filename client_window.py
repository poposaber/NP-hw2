import pygame
from client import Client

class ClientWindow:
    def __init__(self, width=800, height=600, title="Client Window"):
        self.client = Client()
        pygame.init()
        self.width = width
        self.height = height
        self.title = title
        self.screen = pygame.display.set_mode((self.width, self.height))
        pygame.display.set_caption(self.title)
        self.clock = pygame.time.Clock()
        self.running = False

    def run(self):
        self.client.start()
        self.running = True

        while self.running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                    self.client.close()

            self.screen.fill((30, 30, 30))  # Clear screen with dark gray
            pygame.display.flip()  # Update the display
            self.clock.tick(60)  # Limit to 60 frames per second

        pygame.quit()