from ursina import *
import random
import time
import math
import json
import os

# ---------lll Constantes de jeu ---------
BASE_MONSTER_HEALTH = 50 # Vie de base des monstres pour la vague 1

app = Ursina()

# --------- États du jeu ---------
can_move = False
in_combat = False
monsters_alive = 0
wave_counter = 1
monsters_in_wave = 1
is_paused = False
monsters_paused = False
# Variable pour gérer l'état du mouvement avant d'ouvrir le menu d'upgrade/profil
can_move_before_menu = True

# --------- SCÈNE DU JEU ---------
scene_game = Entity(enabled=False)

def game_over():
    global in_combat, can_move
    in_combat = False
    can_move = False
    combat_ui.enabled = False
    if 'upgrade_ui' in globals() and upgrade_ui.enabled: # Fermer le menu d'upgrade si ouvert
        upgrade_ui.enabled = False
    if 'profile_ui' in globals() and profile_ui.enabled: # Fermer le menu de profil si ouvert
        profile_ui.enabled = False
    combat_text.text = "Vous avez été vaincu!"
    combat_text.enabled = True
    print("Game Over")
    invoke(quitter_jeu, delay=2)

class Monster(Entity):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.tag = 'monster'
        self.name = f"Monstre {random.randint(1, 100)}"
        self.max_monster_health = math.ceil(BASE_MONSTER_HEALTH * (1.2 ** (wave_counter - 1)))
        self.health = self.max_monster_health
        self.speed = kwargs.get('speed', 1)
        self.target = player
        self.attack_range = 1
        self.wander_target = self.get_new_wander_target()
        self.health_bar = Entity(parent=self, model='quad', color=color.green, scale=(1, 0.1, 1), position=(0, 1.5, 0))

        # Texte pour afficher les PV du monstre
        self.health_text_display = Text(
            parent=self, # Enfant du monstre
            text=f"{math.ceil(self.health)}/{math.ceil(self.max_monster_health)}",
            position=(0, self.health_bar.y + 0.25, 0), # Positionné légèrement au-dessus de la barre de vie
            scale=8,  # Ajustez cette valeur pour la taille souhaitée
            origin=(0,0),
            color=color.white,
            billboard=True # Pour que le texte fasse toujours face à la caméra
        )

    def get_new_wander_target(self):
        return Vec3(random.uniform(-9, 9), 1, random.uniform(-9, 9))

    def update(self):
        if in_combat or is_paused or monsters_paused or \
            ('upgrade_ui' in globals() and upgrade_ui.enabled) or \
            ('profile_ui' in globals() and profile_ui.enabled):
            return
        distance_to_player = (self.position - self.target.position).length()
        if distance_to_player < 5: # Distance pour suivre le joueur
            direction = (self.target.position - self.position).normalized()
            self.position += direction * self.speed * time.dt
            if distance_to_player <= self.attack_range:
                entrer_combat(self)
        else:
            distance_to_target = (self.position - self.wander_target).length()
            if distance_to_target < 0.5:
                self.wander_target = self.get_new_wander_target()
            else:
                direction = (self.wander_target - self.position).normalized()
                self.position += direction * self.speed * 0.5 * time.dt # Slower wander speed

    def update_health_bar(self):
        current_health = max(0, math.ceil(self.health))
        max_health = math.ceil(self.max_monster_health)

        health_percentage = 0
        if max_health > 0: # Eviter division par zéro
            health_percentage = current_health / max_health

        self.health_bar.scale_x = health_percentage

        # Mettre à jour le texte des PV
        if hasattr(self, 'health_text_display'):
            self.health_text_display.text = f"{current_health}/{max_health}"

        if self.health <= 0:
            combat_button_attack.enabled = False
            combat_button_heavy_attack.enabled = False
            if hasattr(self, 'health_text_display'):
                self.health_text_display.enabled = False
        else:
            if hasattr(self, 'health_text_display'):
                 self.health_text_display.enabled = True

def lancer_jeu():
    global can_move, wave_counter, monsters_in_wave, is_paused, monsters_paused
    global upgrade_button_ui, profile_button_ui, player_health_bar, player_health_text, player_xp_text

    menu_ui.enabled = False
    titre.enabled = False
    bouton_jouer.enabled = False

    scene_game.enabled = True
    player.enabled = True
    gear_button.enabled = True
    pause_button.enabled = True
    wave_text.enabled = True
    xp_text.enabled = True
    can_move = True

    is_paused = False
    monsters_paused = False
    pause_button.text = "Pause"

    upgrade_button_ui.enabled = True
    profile_button_ui.enabled = True
    save_button.enabled = True
    load_button.enabled = True

    if wave_counter == 1:
        monsters_in_wave = 1
        player.max_health = 100
        player.attack_power = 10
        player.base_speed = 5
        player.current_speed_multiplier = 1.0
        player.speed = player.base_speed * player.current_speed_multiplier
        player.upgrade_points = 0 # Reset points pour la nouvelle partie
        # monsters_in_wave est déjà géré par la logique de start_next_wave

    spawn_wave()

    player.health = player.max_health
    if not player_health_bar:
        player_health_bar = Entity(parent=camera.ui, model='quad', color=color.green, scale=(0.3, 0.03), position=(-0.6, -0.45))
    else:
        player_health_bar.enabled = True

    if not player_health_text:
        player_health_text = Text(parent=camera.ui, text=f"{player.health}/{player.max_health}", position=(-0.6, -0.49), origin=(0, 0), scale=1.5, color=color.white)
    else:
        player_health_text.enabled = True

    if not player_xp_text: # Texte XP sur le joueur
        player_xp_text = Text(parent=player, text="XP: 0 / 50", position=(0, 2.1, 0), color=color.white, scale=1, billboard=True) # rendu billboard pour meilleure lisibilité
    else:
        player_xp_text.enabled = True
        player_xp_text.billboard = True

    update_player_health_bar()
    update_xp_ui()
    if 'update_upgrade_display' in globals():
        update_upgrade_display()
    if 'update_profile_display' in globals():
        update_profile_display()

def quitter_jeu():
    global can_move, wave_counter, monsters_in_wave, upgrade_button_ui, profile_button_ui

    if player_health_bar:
        player_health_bar.enabled = False
    if player_health_text:
        player_health_text.enabled = False
    if player_xp_text:
        player_xp_text.enabled = False

    player.enabled = False
    gear_button.enabled = False
    pause_button.enabled = False
    param_menu.enabled = False
    scene_game.enabled = False
    wave_text.enabled = False
    bouton_quitter.enabled = False
    xp_text.enabled = False
    combat_text.enabled = False
    combat_button_attack.enabled = False
    combat_button_heavy_attack.enabled = False
    can_move = False

    if upgrade_button_ui:
        upgrade_button_ui.enabled = False
    if profile_button_ui:
        profile_button_ui.enabled = False
    if 'upgrade_ui' in globals() and upgrade_ui.enabled:
        upgrade_ui.enabled = False
    if 'profile_ui' in globals() and profile_ui.enabled:
        profile_ui.enabled = False

    save_button.enabled = False
    load_button.enabled = False

    player.xp = 0
    player.level = 1
    player.xp_to_next_level = 50
    # player.upgrade_points ne sera pas reset ici, pour conserver la progression si on quitte et relance sans fermer l'app
    # Si on veut un reset total, ajouter player.upgrade_points = 0

    update_xp_ui() # Met à jour l'UI de l'XP pour refléter le reset

    for e in scene_game.children:
        if hasattr(e, 'tag') and e.tag == 'monster':
            destroy(e)

    wave_counter = 1
    monsters_in_wave = 1
    wave_text.text = f"Vague {wave_counter}"
    player.position = Vec3(0, 1, 0)

    titre.enabled = True
    bouton_jouer.enabled = True
    menu_ui.enabled = True

def toggle_param_menu():
    param_menu.enabled = not param_menu.enabled
    bouton_quitter.enabled = param_menu.enabled

def toggle_pause():
    global is_paused, can_move, monsters_paused
    if ('upgrade_ui' in globals() and upgrade_ui.enabled) or \
        ('profile_ui' in globals() and profile_ui.enabled):
        return

    if is_paused:
        pause_button.text = "Pause"
        can_move = True
        monsters_paused = False
        is_paused = False
    else:
        pause_button.text = "Reprendre"
        can_move = False
        monsters_paused = True
        is_paused = True

def toggle_upgrade_menu():
    global can_move, monsters_paused, can_move_before_menu
    if 'profile_ui' in globals() and profile_ui.enabled:
        profile_ui.enabled = False # Ferme le menu profil si ouvert

    upgrade_ui.enabled = not upgrade_ui.enabled
    if upgrade_ui.enabled:
        can_move_before_menu = can_move
        can_move = False
        monsters_paused = True # Pause les monstres quand le menu est ouvert
        update_upgrade_display()
    else:
        can_move = can_move_before_menu
        if not is_paused: # Ne dépause les monstres que si le jeu n'est pas en pause globale
            monsters_paused = False

def update_upgrade_display():
    if 'upgrade_points_text_display' in globals():
        upgrade_points_text_display.text = f"Points: {player.upgrade_points}"
        # Assurer que player.health est un entier pour l'affichage
        hp_current_text.text = f"HP: {math.ceil(player.health)}/{player.max_health}"
        attack_current_text.text = f"Attaque: {player.attack_power}"
        speed_current_text.text = f"Vitesse: {player.speed:.2f} (Mult: {player.current_speed_multiplier:.2f}x)"

def apply_hp_upgrade():
    cost = 1
    if player.upgrade_points >= cost:
        player.upgrade_points -= cost
        player.max_health += 10
        player.health += 10 # Donne aussi de la vie actuelle
        if player.health > player.max_health:
            player.health = player.max_health
        update_player_health_bar()
        update_upgrade_display()
        if 'profile_ui' in globals() and profile_ui.enabled: update_profile_display()
        print(f"HP améliorés! Nouvelle max_health: {player.max_health}")
    else:
        print("Pas assez de points pour améliorer les HP.")

def apply_attack_upgrade():
    cost = 1
    if player.upgrade_points >= cost:
        player.upgrade_points -= cost
        player.attack_power += 5
        update_upgrade_display()
        if 'profile_ui' in globals() and profile_ui.enabled: update_profile_display()
        # Mise à jour des tooltips si le combat est actif (et les boutons visibles)
        if combat_button_attack.enabled: # Implique que l'UI de combat est active
            if combat_button_attack.hovered:
                tooltip_text.text = f"Attaque normale : inflige {player.attack_power} dégâts. 100% de réussite."
            elif combat_button_heavy_attack.hovered:
                tooltip_text.text = f"Attaque lourde : inflige {int(player.attack_power * 1.5)} dégâts. 65% de réussite."
        print(f"Attaque améliorée! Nouvelle attack_power: {player.attack_power}")
    else:
        print("Pas assez de points pour améliorer l'Attaque.")

def apply_speed_upgrade():
    cost = 1
    if player.upgrade_points >= cost:
        player.upgrade_points -= cost
        player.current_speed_multiplier += 0.10
        player.speed = player.base_speed * player.current_speed_multiplier
        update_upgrade_display()
        if 'profile_ui' in globals() and profile_ui.enabled: update_profile_display()
        print(f"Vitesse améliorée! Nouvelle vitesse: {player.speed:.2f}, Multiplicateur: {player.current_speed_multiplier:.2f}x")
    else:
        print("Pas assez de points pour améliorer la Vitesse.")

def toggle_profile_menu():
    global can_move, monsters_paused, can_move_before_menu
    if 'upgrade_ui' in globals() and upgrade_ui.enabled:
        upgrade_ui.enabled = False # Ferme le menu upgrade si ouvert

    profile_ui.enabled = not profile_ui.enabled
    if profile_ui.enabled:
        can_move_before_menu = can_move
        can_move = False
        monsters_paused = True # Pause les monstres quand le menu est ouvert
        update_profile_display()
    else:
        can_move = can_move_before_menu
        if not is_paused: # Ne dépause les monstres que si le jeu n'est pas en pause globale
            monsters_paused = False

def update_profile_display():
    if 'profile_max_hp_text' in globals():
        profile_max_hp_text.text = f"Vie Maximum: {player.max_health}"
        profile_attack_text.text = f"Attaque de Base: {player.attack_power}"
        profile_speed_text.text = f"Vitesse: {player.speed:.2f} (Base: {player.base_speed:.1f}, Mult: {player.current_speed_multiplier:.2f}x)"

def update_xp_ui():
    if 'xp_text' in globals() and xp_text: # UI XP en haut à gauche
        xp_text.text = f"XP: {player.xp} / {player.xp_to_next_level} | Niveau: {player.level}"
    if 'player_xp_text' in globals() and player_xp_text and player_xp_text.enabled: # UI XP sur le joueur
         player_xp_text.text = f"XP: {player.xp} / {player.xp_to_next_level}"

def gain_xp(amount):
    player.xp += amount
    while player.xp >= player.xp_to_next_level:
        player.xp -= player.xp_to_next_level
        player.level += 1
        player.xp_to_next_level = int(player.xp_to_next_level * 1.5) # Augmente le seuil pour le prochain niveau
        player.upgrade_points += 1 # Donne 1 point d'amélioration par niveau
        print(f"Niveau supérieur! +1 point d'amélioration. Total: {player.upgrade_points}")
        if 'upgrade_ui' in globals() and upgrade_ui.enabled:
            update_upgrade_display() # Met à jour l'affichage des points si le menu est ouvert
    update_xp_ui()

def gain_xp_based_on_wave(wave): # Non utilisé actuellement, mais pourrait l'être pour un bonus de fin de vague
    xp_reward = wave * 5
    gain_xp(xp_reward)

def entrer_combat(monstre):
    global in_combat, can_move
    if in_combat or player.health <= 0 or \
        ('upgrade_ui' in globals() and upgrade_ui.enabled) or \
        ('profile_ui' in globals() and profile_ui.enabled):
        return
    in_combat = True
    can_move = False # Empêche le mouvement pendant le combat
    # Affichage des éléments de combat
    combat_ui.enabled = True
    combat_text.enabled = True
    combat_text.text = f"Combat avec {monstre.name}!"
    monstre.health_text_display.enabled = True # S'assurer que le texte de vie du monstre est visible
    player_turn(monstre)

def player_turn(monstre):
    if player.health <= 0:
        game_over()
        return
    # Vérifier si le monstre existe toujours et a de la vie
    if not monstre or not monstre.enabled or monstre.health <= 0:
        finish_combat(monstre if monstre and monstre.health <=0 else None) # S'assure de passer le monstre s'il est mort
        return

    combat_button_attack.enabled = True
    combat_button_heavy_attack.enabled = True
    combat_button_attack.on_click = lambda: attack_monster(monstre)
    combat_button_heavy_attack.on_click = lambda: heavy_attack_monster(monstre)

def attack_monster(monstre):
    if not monstre or not monstre.enabled: return # Sécurité
    print(f"{player.name} attaque {monstre.name}!")
    monstre.health -= player.attack_power
    monstre.update_health_bar() # Met à jour la barre et le texte de PV
    # Désactiver les boutons d'attaque après l'action
    combat_button_attack.enabled = False
    combat_button_heavy_attack.enabled = False

    if monstre.health <= 0:
        finish_combat(monstre)
    else:
        invoke(monster_turn, monstre, delay=1) # Tour du monstre après 1 seconde

def heavy_attack_monster(monstre):
    if not monstre or not monstre.enabled: return # Sécurité
    print(f"{player.name} tente une attaque lourde contre {monstre.name}!")
    damage = int(player.attack_power * 1.5)
    if random.random() < 0.65: # 65% de chance de réussite
        monstre.health -= damage
        print(f"Attaque lourde réussie ! (-{damage} HP)")
    else:
        print("Attaque lourde échouée !")
    monstre.update_health_bar() # Met à jour la barre et le texte de PV
    # Désactiver les boutons d'attaque après l'action
    combat_button_attack.enabled = False
    combat_button_heavy_attack.enabled = False

    if monstre.health <= 0:
        finish_combat(monstre)
    else:
        invoke(monster_turn, monstre, delay=1) # Tour du monstre après 1 seconde

def monster_turn(monstre):
    # Vérifications avant l'attaque du monstre
    if not monstre or not monstre.enabled or monstre.health <= 0 or player.health <= 0:
        if player.health > 0 and (not monstre or not monstre.enabled or monstre.health <=0): # Si le joueur est vivant et le monstre est mort entre-temps
            finish_combat(monstre if monstre and monstre.health <=0 else None)
        return

    print(f"{monstre.name} attaque {player.name}!")
    monster_damage = 10 # Dégâts du monstre (peut être variabilisé)
    player.health -= monster_damage
    update_player_health_bar()

    if player.health <= 0:
        game_over()
    else:
        invoke(player_turn, monstre, delay=1) # Tour du joueur après 1 seconde

def finish_combat(monstre=None): # MODIFIÉ pour le gain de points d'amélioration
    global in_combat, can_move, monsters_alive, wave_counter
    in_combat = False
    # Rendre le mouvement possible seulement si aucun menu n'est ouvert et si le jeu n'est pas en pause
    if not ('upgrade_ui' in globals() and upgrade_ui.enabled) and \
        not ('profile_ui' in globals() and profile_ui.enabled) and \
        not is_paused:
        can_move = True

    combat_ui.enabled = False
    combat_text.enabled = False
    # Masquer le texte de vie du monstre spécifique s'il existe encore (normalement il est détruit)
    if monstre and hasattr(monstre, 'health_text_display'):
        monstre.health_text_display.enabled = False

    if monstre and monstre.health <=0 :
        if monstre.enabled: # S'assurer que le monstre existe avant de le détruire
            # Le texte de vie est enfant du monstre, il sera détruit avec.
            destroy(monstre)

        gain_xp(20)

        # NOUVEAU: Donner un point d'amélioration au joueur pour avoir tué un monstre
        player.upgrade_points += 1
        print(f"Monstre vaincu! +1 point d'amélioration. Points d'amélioration actuels: {player.upgrade_points}")

        if 'upgrade_ui' in globals() and upgrade_ui.enabled:
            update_upgrade_display() # Met à jour l'affichage des points dans le menu

        monsters_alive -= 1
        if monsters_alive <= 0:
            wave_counter += 1
            wave_text.text = "Intermission..."
            invoke(start_next_wave, delay=3) # Lancer la prochaine vague après un délai
    elif not monstre and monsters_alive > 0: # Combat terminé sans tuer le monstre (ex: fuite, pas implémenté)
        # S'assurer que le mouvement est possible si on quitte le combat sans tuer
        pass
    elif monsters_alive <= 0 : # S'il n'y a plus de monstres (par exemple, tous tués en même temps par une AOE future)
        # Cette condition est un peu redondante si la logique ci-dessus est bien suivie, mais sert de garde-fou.
        # S'assure que si monsters_alive est 0, on passe à la vague suivante.
        # 'wave_counter' devrait déjà être incrémenté par le dernier kill.
        # Mais si ce n'est pas le cas (ex: bug ou autre logique future):
        is_any_monster_left = any(e for e in scene_game.children if hasattr(e, 'tag') and e.tag == 'monster' and e.enabled)
        if not is_any_monster_left: # Confirmer qu'il n'y a plus de monstres
            # wave_counter += 1 # Ne pas incrémenter ici si déjà fait
            wave_text.text = "Intermission..." # Peut-être déjà fait
            invoke(start_next_wave, delay=3)

def start_next_wave():
    global monsters_in_wave

    player.health = player.max_health
    update_player_health_bar()

    if 'upgrade_ui' in globals() and upgrade_ui.enabled:
        update_upgrade_display()
    # if 'profile_ui' in globals() and profile_ui.enabled: # Profil n'affiche pas la vie actuelle directement
        # update_profile_display()

    wave_text.text = f"Vague {wave_counter}"
    if wave_counter <= 10:
        monsters_in_wave = wave_counter
    else:
        monsters_in_wave = math.ceil(monsters_in_wave * 1.2) # Augmentation du nombre pour vagues > 10

    spawn_wave()

def spawn_wave():
    global monsters_alive
    monsters_alive = monsters_in_wave
    for _ in range(monsters_in_wave):
        spawn_monster()

def spawn_monster():
    monster_type = random.choice(['fast', 'normal', 'slow'])
    if monster_type == 'fast':
        speed = 3
        color_choice = color.blue
    elif monster_type == 'normal':
        speed = 1.5
        color_choice = color.yellow
    else: # slow
        speed = 1
        color_choice = color.red

    Monster(
        parent=scene_game,
        model='cube',
        color=color_choice,
        scale=(1, 2, 1), # Hauteur de 2 unités
        position=(random.randint(-10, 10), 1, random.randint(-10, 10)), # Monstre posé sur y=0 (centre à y=1)
        collider='box',
        speed=speed
    )

def update_player_health_bar():
    if player_health_bar and player:
        health_percentage = 0
        if player.max_health > 0:
            health_percentage = player.health / player.max_health
        player_health_bar.scale_x = max(health_percentage * 0.3, 0)

    if player_health_text and player:
        player_health_text.text = f"{math.ceil(max(player.health, 0))}/{player.max_health}"

def update():
    if can_move and not is_paused and not in_combat and \
        not ('upgrade_ui' in globals() and upgrade_ui.enabled) and \
        not ('profile_ui' in globals() and profile_ui.enabled):
        current_move_speed = player.speed * time.dt
        # Mouvements du joueur
        if held_keys['w'] or held_keys['z']:
            if player.position.z < 10: # Limite de la carte
                player.position += player.forward * current_move_speed
        if held_keys['s']:
            if player.position.z > -10: # Limite de la carte
                player.position -= player.forward * current_move_speed
        if held_keys['a'] or held_keys['q']:
            if player.position.x > -10: # Limite de la carte
                player.position -= player.right * current_move_speed
        if held_keys['d']:
            if player.position.x < 10: # Limite de la carte
                player.position += player.right * current_move_speed

        # Caméra suit le joueur
        camera.position = Vec3(player.position.x, 10, player.position.z - 20)

    # Tooltips pour les boutons d'attaque
    if combat_button_attack and combat_button_attack.enabled and combat_button_attack.hovered:
        tooltip_text.text = f"Attaque normale : inflige {player.attack_power} dégâts. 100% de réussite."
        tooltip_text.enabled = True
    elif combat_button_heavy_attack and combat_button_heavy_attack.enabled and combat_button_heavy_attack.hovered:
        tooltip_text.text = f"Attaque lourde : inflige {int(player.attack_power * 1.5)} dégâts. 65% de réussite."
        tooltip_text.enabled = True
    else:
        tooltip_text.enabled = False

def save_game():
    game_state = {
        'player': {
            'health': player.health,
            'max_health': player.max_health,
            'attack_power': player.attack_power,
            'speed': player.speed,
            'base_speed': player.base_speed,
            'current_speed_multiplier': player.current_speed_multiplier,
            'xp': player.xp,
            'level': player.level,
            'xp_to_next_level': player.xp_to_next_level,
            'upgrade_points': player.upgrade_points,
            'position': list(player.position)
        },
        'wave_counter': wave_counter,
        'monsters_in_wave': monsters_in_wave,
        'monsters_alive': monsters_alive
    }

    with open('save_game.json', 'w') as file:
        json.dump(game_state, file)
    print("Game saved!")

def load_game():
    global wave_counter, monsters_in_wave, monsters_alive

    if os.path.exists('save_game.json'):
        with open('save_game.json', 'r') as file:
            game_state = json.load(file)

        player.health = game_state['player']['health']
        player.max_health = game_state['player']['max_health']
        player.attack_power = game_state['player']['attack_power']
        player.speed = game_state['player']['speed']
        player.base_speed = game_state['player']['base_speed']
        player.current_speed_multiplier = game_state['player']['current_speed_multiplier']
        player.xp = game_state['player']['xp']
        player.level = game_state['player']['level']
        player.xp_to_next_level = game_state['player']['xp_to_next_level']
        player.upgrade_points = game_state['player']['upgrade_points']

        # Correctly load the player's position as a Vec3 object
        player.position = Vec3(game_state['player']['position'][0],
                               game_state['player']['position'][1],
                               game_state['player']['position'][2])

        wave_counter = game_state['wave_counter']
        monsters_in_wave = game_state['monsters_in_wave']
        monsters_alive = game_state['monsters_alive']

        update_player_health_bar()
        update_xp_ui()
        if 'update_upgrade_display' in globals():
            update_upgrade_display()
        if 'update_profile_display' in globals():
            update_profile_display()

        print("Game loaded!")
    else:
        print("No saved game found.")

# --- Initialisation des Éléments UI et Entités ---
menu_ui = Entity(enabled=True)
titre = Text("THE LAST OF PYTHON", origin=(0, 0), scale=2, y=0.4)
bouton_jouer = Button(text="JOUER", scale=(0.3, 0.1), y=0, color=color.azure)
bouton_jouer.on_click = lancer_jeu

game_ui = Entity(parent=scene_game, enabled=False)

player = Entity(parent=scene_game, model='cube', color=color.orange, scale_y=2, position=(0, 1, 0), enabled=False, name="Joueur")
player.xp = 0
player.level = 1
player.xp_to_next_level = 50
player.health = 100
player.max_health = 100
player.attack_power = 10
player.base_speed = 5
player.current_speed_multiplier = 1.0
player.speed = player.base_speed * player.current_speed_multiplier
player.upgrade_points = 0

player_health_bar = None
player_health_text = None
player_xp_text = None

xp_text = Text(parent=camera.ui, text="XP: 0 / 50 | Niveau: 1", position=(-0.7, 0.4), scale=1.5, enabled=False) # UI XP en haut

gear_button = Button(parent=camera.ui, texture="vrai_engrenage.png", scale=0.08, position=window.top_right - Vec2(0.07, 0.07), enabled=False)
gear_button.on_click = toggle_param_menu

pause_button = Button(parent=camera.ui, text="Pause", scale=0.08, position=window.top_right - Vec2(0.15, 0.07), enabled=False)
pause_button.on_click = toggle_pause

upgrade_button_ui = Button(parent=camera.ui, text="Upgrade", color=color.gold, scale=(0.15, 0.06), position=window.left + Vec2(0.1, 0.05), enabled=False)
upgrade_button_ui.on_click = toggle_upgrade_menu

profile_button_ui = Button(parent=camera.ui, text="Profil", color=color.cyan, scale=(0.15, 0.06), position=window.left + Vec2(0.1, -0.02), enabled=False)
profile_button_ui.on_click = toggle_profile_menu

save_button = Button(parent=camera.ui, text="Save Game", scale=(0.15, 0.06), position=window.left + Vec2(0.1, -0.09), enabled=False)
save_button.on_click = save_game

load_button = Button(parent=camera.ui, text="Load Game", scale=(0.15, 0.06), position=window.left + Vec2(0.1, -0.16), enabled=False)
load_button.on_click = load_game

# --- Interface d'Amélioration (Upgrade UI) ---
upgrade_ui = Entity(parent=camera.ui, enabled=False, z=-1)
upgrade_background_panel = Entity(parent=upgrade_ui, model='quad', color=color.rgba(0,0,0,200), scale=(0.75, 0.65), z=0)
upgrade_title_text = Text("Améliorations", parent=upgrade_ui, origin=(0,0), y=0.26, scale=1.8, color=color.white, z=-1)
upgrade_points_text_display = Text(f"Points: {player.upgrade_points}", parent=upgrade_ui, origin=(0,0), y=0.18, scale=1.2, color=color.white, z=-1)

hp_current_text = Text(f"HP: {math.ceil(player.health)}/{player.max_health}", parent=upgrade_ui, origin=(-0.5,0), x=-0.3, y=0.08, scale=1.1, color=color.white, z=-1)
hp_upgrade_button_ui = Button(text="HP (+10)", parent=upgrade_ui, color=color.green, scale=(0.25, 0.06), x=0.15, y=0.08, z=-1)
hp_upgrade_button_ui.on_click = apply_hp_upgrade

attack_current_text = Text(f"Attaque: {player.attack_power}", parent=upgrade_ui, origin=(-0.5,0), x=-0.3, y=0.00, scale=1.1, color=color.white, z=-1)
attack_upgrade_button_ui = Button(text="Attaque (+5)", parent=upgrade_ui, color=color.red, scale=(0.25, 0.06), x=0.15, y=0.00, z=-1)
attack_upgrade_button_ui.on_click = apply_attack_upgrade

speed_current_text = Text(f"Vitesse: {player.speed:.2f}", parent=upgrade_ui, origin=(-0.5,0), x=-0.3, y=-0.08, scale=1.1, color=color.white, z=-1)
speed_upgrade_button_ui = Button(text="Vitesse (+10%)", parent=upgrade_ui, color=color.blue, scale=(0.28, 0.06), x=0.15, y=-0.08, z=-1)
speed_upgrade_button_ui.on_click = apply_speed_upgrade

close_upgrade_panel_button = Button(text="Fermer", parent=upgrade_ui, color=color.gray, scale=(0.2, 0.06), y=-0.24, z=-1)
close_upgrade_panel_button.on_click = toggle_upgrade_menu

# --- Interface de Profil ---
profile_ui = Entity(parent=camera.ui, enabled=False, z=-1)
profile_background_panel = Entity(parent=profile_ui, model='quad', color=color.rgba(20,20,20,220), scale=(0.6, 0.5), z=0)
profile_title_text = Text("Profil du Joueur", parent=profile_ui, origin=(0,0), y=0.18, scale=1.8, color=color.white, z=-1)

profile_max_hp_text = Text(f"Vie Maximum: {player.max_health}", parent=profile_ui, origin=(0,0), y=0.05, scale=1.2, color=color.white, z=-1)
profile_attack_text = Text(f"Attaque de Base: {player.attack_power}", parent=profile_ui, origin=(0,0), y=-0.02, scale=1.2, color=color.white, z=-1)
profile_speed_text = Text(f"Vitesse: {player.speed:.2f}", parent=profile_ui, origin=(0,0), y=-0.09, scale=1.2, color=color.white, z=-1)

close_profile_panel_button = Button(text="Fermer", parent=profile_ui, color=color.gray, scale=(0.2, 0.06), y=-0.18, z=-1)
close_profile_panel_button.on_click = toggle_profile_menu

param_menu = Entity(parent=camera.ui, enabled=False) # Parenté à camera.ui pour une meilleure gestion de la visibilité
bouton_quitter = Button(parent=param_menu, text="Quitter", scale=(0.3, 0.1), color=color.red, position=(0, 0), enabled=True) # enabled=True car parent est disabled au début
bouton_quitter.on_click = quitter_jeu

terrain = Entity(parent=scene_game, model='plane', texture='white_cube', scale=(20, 1, 20), color=color.green, collider='box')

wall_thickness = 1
walls = [
    Entity(parent=scene_game, model='cube', color=color.clear, scale=(wall_thickness, 3, 20), position=(10, 1.5, 0), collider='box', visible=False),
    Entity(parent=scene_game, model='cube', color=color.clear, scale=(wall_thickness, 3, 20), position=(-10, 1.5, 0), collider='box', visible=False),
    Entity(parent=scene_game, model='cube', color=color.clear, scale=(20, 3, wall_thickness), position=(0, 1.5, 10), collider='box', visible=False),
    Entity(parent=scene_game, model='cube', color=color.clear, scale=(20, 3, wall_thickness), position=(0, 1.5, -10), collider='box', visible=False)
]

wave_text = Text(f"Vague {wave_counter}", parent=camera.ui, origin=(0, 0), position=(0, 0.45), scale=2, color=color.white, enabled=False)

camera.position = (0, 10, -20) # Position initiale de la caméra
camera.rotation = (25, 0, 0) # Rotation initiale de la caméra

combat_ui = Entity(parent=camera.ui, enabled=False) # Parenté à camera.ui pour l'UI de combat
combat_text = Text("Combat", parent=combat_ui, origin=(0, 0), position=(0, 0.3), scale=2, color=color.white, enabled=True) # enabled=True si parent est enabled
combat_button_attack = Button(parent=combat_ui, text="Attaquer", scale=(0.3, 0.1), position=(-0.2, -0.4), enabled=True)
combat_button_heavy_attack = Button(parent=combat_ui, text="Attaque lourde", scale=(0.3, 0.1), position=(0.2, -0.4), enabled=True)

tooltip_text = Text(parent=camera.ui, text="", position=(0, -0.25), origin=(0, 0), scale=1.5, color=color.white, enabled=False)

def input(key):
    pass

app.run()

