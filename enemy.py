import pygame

from entity import Entity

from settings import *
from utils import *

class Enemy(Entity):

    def __init__(self, monster_name, pos, groups, obstacle_sprites, hit_player, death_effect, get_exp):
        super().__init__(groups)

        self.sprite_type = 'enemy'
        self.obstacle_sprites = obstacle_sprites
        self.display_surface = pygame.display.get_surface()

        # Graphic setup
        self.import_graphics(monster_name)
        self.status = 'idle'
        self.image = self.animations[self.status][self.frame_index]
        self.death_effect = death_effect

        # Movement setup
        self.rect = self.image.get_rect(topleft = pos)
        self.hitbox = self.rect.inflate(0, -10)

        # Stats
        self.monster_name = monster_name
        monster_info = enemy_data[monster_name]
        self.max_health = monster_info['health']
        self.health = self.max_health
        self.exp = monster_info['exp']
        self.normal_speed = monster_info['speed']
        self.speed = self.normal_speed
        self.attack_damage = monster_info['damage']
        self.attack_type = monster_info['attack_type']
        self.attack_radius = monster_info['attack_radius']
        self.resistance = monster_info['resistance']
        self.notice_radius = monster_info['notice_radius']

        # Player interaction
        self.can_attack = True
        self.attack_cooldown = 500
        self.attack_time = None
        self.hit_player = hit_player
        self.get_exp = get_exp

        # Invincibility setup
        self.vulnerable = True
        self.hit_time = None
        self.invincibility_duration = 300

        # Flee setup
        self.safe_distance = 500
        self.health_threshold = self.max_health * 0.60
        self.recovery_rate = 0.2

        # Health bar
        self.health_bar = pygame.Rect(self.rect.left, self.rect.top - 15, self.rect.width, 10)

        # Sounds
        self.death_sound = pygame.mixer.Sound('../audio/death.wav')
        self.attack_sound = pygame.mixer.Sound(monster_info['attack_sound'])
        self.death_sound.set_volume(0.15)
        self.attack_sound.set_volume(0.15)

    def import_graphics(self, name):
        base_path = f'../graphics/monsters/{name}/'

        self.animations = {'idle': [], 'move': [], 'attack': [], 'flee': []}
        for animation in self.animations.keys():
            self.animations[animation] = import_folder(base_path + animation)

    def get_player_direction_distance(self, player):
        enemy_vec = pygame.math.Vector2(self.rect.center)
        player_vec = pygame.math.Vector2(player.rect.center)

        distance = (player_vec - enemy_vec).magnitude()

        if distance > 0:
            direction = (player_vec - enemy_vec).normalize()
        else:
            direction = pygame.math.Vector2()

        return (direction, distance)

    def get_status(self, player):
        distance = self.get_player_direction_distance(player)[1]

        if self.health <= self.health_threshold and distance < self.safe_distance:
            self.status = 'flee'

        elif distance <= self.attack_radius and self.can_attack:
            if self.status != 'attack':
                self.frame_index = 0

            self.attack_time = pygame.time.get_ticks()
            self.status = 'attack'
        
        elif distance <= self.notice_radius:
            self.status = 'move'
        
        else:
            self.status = 'idle'

    def actions(self, player):
        if self.status == 'attack':
            self.hit_player(self.attack_damage, self.attack_type)
            self.attack_sound.play()
        
        elif self.status == 'move':
            self.direction = self.get_player_direction_distance(player)[0]

        elif self.status == 'flee':
            self.speed = self.normal_speed * 1.5
            self.health = min(self.health + self.recovery_rate, self.max_health)
        
        else:
            self.direction = pygame.math.Vector2()
            self.speed = self.normal_speed
            self.health = min(self.health + self.recovery_rate, self.max_health)

    def animate(self):
        animation = self.animations[self.status]

        self.frame_index += self.animation_speed
        if self.frame_index >= len(animation):
            if self.status == 'attack':
                self.can_attack = False

            self.frame_index = 0
        
        self.image = animation[int(self.frame_index)]
        self.rect = self.image.get_rect(center = self.hitbox.center)

        # Flicker effect on getting hit
        self.flicker()

    def cooldown(self):
        current_time = pygame.time.get_ticks()

        if not self.can_attack:
            if current_time - self.attack_time >= self.attack_cooldown:
                self.can_attack = True

        if not self.vulnerable:
            if current_time - self.hit_time >= self.invincibility_duration:
                self.vulnerable = True

    def take_damage(self, player, attack_type):
        if self.vulnerable:
            self.direction = self.get_player_direction_distance(player)[0]
            self.health -= player.get_full_attack_stat(attack_type)

            self.hit_time = pygame.time.get_ticks()
            self.vulnerable = False

    def hit_reaction(self):
        if not self.vulnerable:
            self.direction *= -self.resistance

    def draw_health_bar(self, camera_offset):
        # Adjust health bar position by camera offset
        health_bar_pos = (self.health_bar.left - camera_offset.x, self.health_bar.top - camera_offset.y)

        # Create the background bar
        bg_bar_rect = pygame.Rect(health_bar_pos, (self.health_bar.width, self.health_bar.height))
        pygame.draw.rect(self.display_surface, UI_BG_COLOR, bg_bar_rect)

        # Convert int stats to pixels
        ratio = self.health / self.max_health
        curr_width = self.health_bar.width * ratio
        curr_rect = pygame.Rect(health_bar_pos, (curr_width, self.health_bar.height))

        # Draw the bar
        pygame.draw.rect(self.display_surface, HEALTH_COLOR, curr_rect)

        # Draw the border
        pygame.draw.rect(self.display_surface, UI_BORDER_COLOR, bg_bar_rect, 2)

    def check_death(self):
        if self.health <= 0:
            self.death_effect(self.rect.center, self.monster_name)
            self.kill()
            self.death_sound.play()
            self.get_exp(self.exp)

    def update(self):
        self.check_death()
        self.hit_reaction()
        self.move(self.speed)
        self.animate()
        self.cooldown()

    def enemy_update(self, player, camera_offset):
        self.get_status(player)
        self.actions(player)

        self.health_bar.topleft = (self.rect.left, self.rect.top - 15) # Update health bar position acc. to enemy posiion
        self.draw_health_bar(camera_offset)
