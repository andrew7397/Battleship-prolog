import sys
import random
import pygame
from pyswip import Prolog


pygame.init()


GRID_SIZE = 10
CELL_SIZE = 40
MARGIN = 5
GRID_WIDTH = GRID_SIZE * (CELL_SIZE + MARGIN) - MARGIN
GRID_HEIGHT = GRID_SIZE * (CELL_SIZE + MARGIN) - MARGIN
SCREEN_WIDTH = 2 * GRID_WIDTH + 100
SCREEN_HEIGHT = GRID_HEIGHT + 200


WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
BLUE = (0, 0, 255)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
GRAY = (128, 128, 128)
LIGHT_GRAY = (200, 200, 200)
DARK_BLUE = (0, 0, 139)


WATER = 0
SHIP = 1
HIT = 2
MISS = 3


class BattleshipGame:
    def __init__(self):
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Battaglia Navale - Python + Prolog")
        self.clock = pygame.time.Clock()
        
        self.player_grid = [[WATER for _ in range(GRID_SIZE)] for _ in range(GRID_SIZE)]
        self.ai_grid = [[WATER for _ in range(GRID_SIZE)] for _ in range(GRID_SIZE)]
        

        self.player_shots = [[WATER for _ in range(GRID_SIZE)] for _ in range(GRID_SIZE)]
        self.ai_shots = [[WATER for _ in range(GRID_SIZE)] for _ in range(GRID_SIZE)]
        
        
        self.ship_sizes = [1, 2, 3, 2, 3]
        
        
        self.game_state = "placing"  # placing, playing, game_over
        self.current_ship = 0
        self.ship_orientation = "horizontal" 
        self.player_turn = True
        self.winner = None
        self.sunk_ships = []  
        self.font = pygame.font.Font(None, 24)
        self.big_font = pygame.font.Font(None, 48)
        self.prolog = Prolog()
        self.init_prolog()
        self.place_ai_ships()
        
    def init_prolog(self):
        """Inizializza la knowledge base per prolog"""
        self.prolog.assertz("grid_size(10)")
        
        
        fleet_info = {}
        for size in self.ship_sizes:
            fleet_info[size] = fleet_info.get(size, 0) + 1
        
        for size, count in fleet_info.items():
            self.prolog.assertz(f"ship_size({size})")
            self.prolog.assertz(f"ship_count({size}, {count})")
        
        
        total_ships = len(self.ship_sizes)
        self.prolog.assertz(f"total_ships({total_ships})")
        
        # Predicato per le celle valide
        for i in range(GRID_SIZE):
            for j in range(GRID_SIZE):
                self.prolog.assertz(f"valid_cell({i}, {j})")
        
        
        # Predicati per il 4-connesso
        self.prolog.assertz("adjacent(X1, Y1, X2, Y2) :- X2 is X1 + 1, Y2 = Y1, valid_cell(X2, Y2)")
        self.prolog.assertz("adjacent(X1, Y1, X2, Y2) :- X2 is X1 - 1, Y2 = Y1, valid_cell(X2, Y2)")
        self.prolog.assertz("adjacent(X1, Y1, X2, Y2) :- X2 = X1, Y2 is Y1 + 1, valid_cell(X2, Y2)")
        self.prolog.assertz("adjacent(X1, Y1, X2, Y2) :- X2 = X1, Y2 is Y1 - 1, valid_cell(X2, Y2)")
        
        # Direzioni
        self.prolog.assertz("direction(horizontal)")
        self.prolog.assertz("direction(vertical)")
        
        # Strategia di base ovvero non colpire celle già colpite
        self.prolog.assertz("can_shoot(X, Y) :- valid_cell(X, Y), \\+ shot(X, Y)")
        
        
        # Una cella appartiene a una nave affondata se è parte di un ship_sunk
        self.prolog.assertz("belongs_to_sunk_ship(X, Y) :- ship_sunk(ShipId), ship_cell(ShipId, X, Y)")
        
        # Un hit è "attivo" (da seguire) solo se non appartiene a una nave già affondata
        self.prolog.assertz("active_hit(X, Y) :- hit(X, Y), \\+ belongs_to_sunk_ship(X, Y)")
        
        # Due hit attivi sono sulla stessa linea
        self.prolog.assertz("same_row_active(X1, Y1, X2, Y2) :- active_hit(X1, Y1), active_hit(X2, Y2), X1 = X2, Y1 \\= Y2")
        self.prolog.assertz("same_column_active(X1, Y1, X2, Y2) :- active_hit(X1, Y1), active_hit(X2, Y2), Y1 = Y2, X1 \\= X2")
        
        # Direzione di una nave attiva (non ancora affondata)
        self.prolog.assertz("active_ship_direction(X1, Y1, X2, Y2, horizontal) :- same_row_active(X1, Y1, X2, Y2), adjacent(X1, Y1, X2, Y2)")
        self.prolog.assertz("active_ship_direction(X1, Y1, X2, Y2, vertical) :- same_column_active(X1, Y1, X2, Y2), adjacent(X1, Y1, X2, Y2)")
        
        
        # Continua lungo la direzione di una nave attiva
        self.prolog.assertz("continue_active_horizontal(X, Y1, Y2, X, Y3) :- Y1 < Y2, Y3 is Y1 - 1, can_shoot(X, Y3), \\+ belongs_to_sunk_ship(X, Y3)")
        self.prolog.assertz("continue_active_horizontal(X, Y1, Y2, X, Y3) :- Y1 < Y2, Y3 is Y2 + 1, can_shoot(X, Y3), \\+ belongs_to_sunk_ship(X, Y3)")
        self.prolog.assertz("continue_active_horizontal(X, Y1, Y2, X, Y3) :- Y1 > Y2, Y3 is Y2 - 1, can_shoot(X, Y3), \\+ belongs_to_sunk_ship(X, Y3)")
        self.prolog.assertz("continue_active_horizontal(X, Y1, Y2, X, Y3) :- Y1 > Y2, Y3 is Y1 + 1, can_shoot(X, Y3), \\+ belongs_to_sunk_ship(X, Y3)")
        
        self.prolog.assertz("continue_active_vertical(X1, Y, X2, Y, X3, Y) :- X1 < X2, X3 is X1 - 1, can_shoot(X3, Y), \\+ belongs_to_sunk_ship(X3, Y)")
        self.prolog.assertz("continue_active_vertical(X1, Y, X2, Y, X3, Y) :- X1 < X2, X3 is X2 + 1, can_shoot(X3, Y), \\+ belongs_to_sunk_ship(X3, Y)")
        self.prolog.assertz("continue_active_vertical(X1, Y, X2, Y, X3, Y) :- X1 > X2, X3 is X2 - 1, can_shoot(X3, Y), \\+ belongs_to_sunk_ship(X3, Y)")
        self.prolog.assertz("continue_active_vertical(X1, Y, X2, Y, X3, Y) :- X1 > X2, X3 is X1 + 1, can_shoot(X3, Y), \\+ belongs_to_sunk_ship(X3, Y)")
        
        # Continua lungo la direzione identificata per navi attive
        self.prolog.assertz("continue_active_direction(X1, Y1, X2, Y2, X3, Y3) :- active_ship_direction(X1, Y1, X2, Y2, horizontal), continue_active_horizontal(X1, Y1, Y2, X3, Y3)")
        self.prolog.assertz("continue_active_direction(X1, Y1, X2, Y2, X3, Y3) :- active_ship_direction(X1, Y1, X2, Y2, vertical), continue_active_vertical(X1, Y1, X2, Y2, X3, Y3)")
        
        # Hit isolato attivo (non appartiene a nave affondata e non ha hit adiacenti attivi)
        self.prolog.assertz("isolated_active_hit(X, Y) :- active_hit(X, Y), \\+ (adjacent(X, Y, X2, Y2), active_hit(X2, Y2))")
        
        # Colpo adiacente a hit attivo isolato
        self.prolog.assertz("adjacent_to_isolated_hit(X1, Y1, X2, Y2) :- isolated_active_hit(X1, Y1), adjacent(X1, Y1, X2, Y2), can_shoot(X2, Y2), \\+ belongs_to_sunk_ship(X2, Y2)")
        
        # Continua da singolo hit attivo
        self.prolog.assertz("continue_from_active_hit(X1, Y1, X2, Y2) :- isolated_active_hit(X1, Y1), adjacent(X1, Y1, X2, Y2), can_shoot(X2, Y2), \\+ belongs_to_sunk_ship(X2, Y2)")
        
        # Strategia per aree ad alta probabilità (evita zone intorno a navi affondate)
        self.prolog.assertz("high_probability_cell(X, Y) :- can_shoot(X, Y), \\+ near_sunk_ship(X, Y)")
        self.prolog.assertz("near_sunk_ship(X, Y) :- ship_sunk(ShipId), ship_cell(ShipId, X2, Y2), adjacent(X, Y, X2, Y2)")
        
        
    def place_ai_ships(self):
        """Piazza le navi dell'AI casualmente"""
        for ship_size in self.ship_sizes:
            placed = False
            attempts = 0
            while not placed and attempts < 100:
                x = random.randint(0, GRID_SIZE - 1)
                y = random.randint(0, GRID_SIZE - 1)
                orientation = random.choice(["horizontal", "vertical"])
                
                if self.can_place_ship(self.ai_grid, x, y, ship_size, orientation):
                    self.place_ship(self.ai_grid, x, y, ship_size, orientation)
                    placed = True
                attempts += 1
                
    def can_place_ship(self, grid, x, y, size, orientation):
        """Verifica se una nave può essere piazzata"""
        if orientation == "horizontal":
            if y + size > GRID_SIZE:
                return False
            for i in range(size):
                if grid[x][y + i] != WATER:
                    return False
        else:  # vertical
            if x + size > GRID_SIZE:
                return False
            for i in range(size):
                if grid[x + i][y] != WATER:
                    return False
        return True
        
    def place_ship(self, grid, x, y, size, orientation):
        """Piazza una nave sulla griglia"""
        if orientation == "horizontal":
            for i in range(size):
                grid[x][y + i] = SHIP
        else:  # vertical
            for i in range(size):
                grid[x + i][y] = SHIP
                
    def get_cell_from_mouse(self, mouse_pos, grid_offset_x):
        """Converte posizione mouse in coordinate griglia"""
        x, y = mouse_pos
        x -= grid_offset_x
        
        if x < 0 or x >= GRID_WIDTH or y < 50 or y >= GRID_HEIGHT + 50:
            return None, None
            
        cell_x = (y - 50) // (CELL_SIZE + MARGIN)
        cell_y = x // (CELL_SIZE + MARGIN)
        
        if 0 <= cell_x < GRID_SIZE and 0 <= cell_y < GRID_SIZE:
            return cell_x, cell_y
        return None, None
        
    def handle_player_placement(self, mouse_pos):
        """Gestisce il piazzamento delle navi del giocatore"""
        if self.current_ship >= len(self.ship_sizes):
            return
            
        cell_x, cell_y = self.get_cell_from_mouse(mouse_pos, 50)
        if cell_x is None:
            return
            
        ship_size = self.ship_sizes[self.current_ship]
        
        if self.can_place_ship(self.player_grid, cell_x, cell_y, ship_size, self.ship_orientation):
            self.place_ship(self.player_grid, cell_x, cell_y, ship_size, self.ship_orientation)
            self.current_ship += 1
            
            if self.current_ship >= len(self.ship_sizes):
                self.game_state = "playing"
                
    def handle_player_shot(self, mouse_pos):
        """Gestisce i colpi del giocatore"""
        if not self.player_turn:
            return
            
        cell_x, cell_y = self.get_cell_from_mouse(mouse_pos, GRID_WIDTH + 100)
        if cell_x is None:
            return
            
        if self.player_shots[cell_x][cell_y] != WATER:
            return  # Già colpito
            
        if self.ai_grid[cell_x][cell_y] == SHIP:
            self.player_shots[cell_x][cell_y] = HIT
            self.ai_grid[cell_x][cell_y] = HIT
        else:
            self.player_shots[cell_x][cell_y] = MISS
            
        self.player_turn = False
        self.check_winner()
        
    def ai_turn(self):
        """Turno dell'AI usando logica Prolog"""
        if self.player_turn:
            return
            
        # Aggiorna la knowledge base con i colpi precedenti
        self.update_prolog_knowledge()
        target = self.get_ai_target()
        
        if target:
            x, y = target
            # Aggiorna Prolog che abbiamo sparato
            self.prolog.assertz(f"shot({x}, {y})")
            
            if self.player_grid[x][y] == SHIP:
                self.ai_shots[x][y] = HIT
                self.player_grid[x][y] = HIT
                self.prolog.assertz(f"hit({x}, {y})")
                print(f"AI: HIT su ({x}, {y})")
                
                # Controlla se una nave è stata affondata
                self.check_and_mark_sunk_ships()
                
            else:
                self.ai_shots[x][y] = MISS
                self.prolog.assertz(f"miss({x}, {y})")
                print(f"AI: MISS su ({x}, {y})")
                
        self.player_turn = True
        self.check_winner()
        
    def update_prolog_knowledge(self):
        """Aggiorna la knowledge base Prolog con lo stato attuale"""
        # Pulisce e riaggiorna i fatti dinamici
        try:
            self.prolog.retractall("shot(_, _)")
            self.prolog.retractall("hit(_, _)")
            self.prolog.retractall("miss(_, _)")
            self.prolog.retractall("ship_sunk(_)")
            self.prolog.retractall("ship_cell(_, _, _)")
        except:
            pass
        
        # Aggiorna stato delle celle
        for i in range(GRID_SIZE):
            for j in range(GRID_SIZE):
                if self.ai_shots[i][j] == HIT:
                    self.prolog.assertz(f"shot({i}, {j})")
                    self.prolog.assertz(f"hit({i}, {j})")
                elif self.ai_shots[i][j] == MISS:
                    self.prolog.assertz(f"shot({i}, {j})")
                    self.prolog.assertz(f"miss({i}, {j})")
        
        # Aggiorna le navi affondate nella knowledge base
        for ship_id, ship_cells in enumerate(self.sunk_ships):
            self.prolog.assertz(f"ship_sunk({ship_id})")
            for x, y in ship_cells:
                self.prolog.assertz(f"ship_cell({ship_id}, {x}, {y})")
                
    def check_and_mark_sunk_ships(self):
        """Controlla se nuove navi sono state affondate e le aggiunge alla lista"""
        # Trova tutti i cluster di hit connessi
        visited = set()
        current_sunk = set()
        
        for i in range(GRID_SIZE):
            for j in range(GRID_SIZE):
                if self.ai_shots[i][j] == HIT and (i, j) not in visited:
                    cluster = self.find_hit_cluster(i, j, visited)
                    if self.is_ship_sunk(cluster):
                        current_sunk.add(frozenset(cluster))
        
        # Aggiunge nuove navi affondate
        existing_sunk = set(frozenset(ship) for ship in self.sunk_ships)
        new_sunk_ships = current_sunk - existing_sunk
        
        for new_ship in new_sunk_ships:
            self.sunk_ships.append(list(new_ship))
            print(f"AI: Nave affondata rilevata: {list(new_ship)}")
    
    def find_hit_cluster(self, start_x, start_y, visited):
        """Trova un cluster di hit connessi usando DFS"""
        cluster = []
        stack = [(start_x, start_y)]
        
        while stack:
            x, y = stack.pop()
            if (x, y) in visited or self.ai_shots[x][y] != HIT:
                continue
                
            visited.add((x, y))
            cluster.append((x, y))
            
            # Controlla celle adiacenti
            for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                nx, ny = x + dx, y + dy
                if (0 <= nx < GRID_SIZE and 0 <= ny < GRID_SIZE and 
                    (nx, ny) not in visited and self.ai_shots[nx][ny] == HIT):
                    stack.append((nx, ny))
        
        return cluster
    
    def is_ship_sunk(self, cluster):
        """Verifica se un cluster di hit rappresenta una nave completamente affondata"""
        if not cluster:
            return False
        
        # Ordina il cluster per verificare se forma una linea
        cluster.sort()
        
        # Verifica se è una singola cella (nave di dimensione 1)
        if len(cluster) == 1:
            x, y = cluster[0]
            # Controlla che non ci siano celle adiacenti d'acqua che potrebbero essere parte della nave
            for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                nx, ny = x + dx, y + dy
                if (0 <= nx < GRID_SIZE and 0 <= ny < GRID_SIZE):
                    if self.ai_shots[nx][ny] == WATER:
                        # Se la cella adiacente è acqua non colpita, la nave potrebbe continuare
                        return False
            return True
        
        # Per navi di dimensione > 1, verifica che formino una linea continua
        # e che non ci siano celle adiacenti non colpite alle estremità
        if self.forms_continuous_line(cluster):
            return self.check_ship_endpoints(cluster)
        
        return False
    
    def forms_continuous_line(self, cluster):
        """Verifica se il cluster forma una linea continua"""
        if len(cluster) <= 1:
            return True
        
        cluster.sort()
        
        # Controlla se è orizzontale
        if all(pos[0] == cluster[0][0] for pos in cluster):
            for i in range(1, len(cluster)):
                if cluster[i][1] - cluster[i-1][1] != 1:
                    return False
            return True
        
        # Controlla se è verticale
        if all(pos[1] == cluster[0][1] for pos in cluster):
            for i in range(1, len(cluster)):
                if cluster[i][0] - cluster[i-1][0] != 1:
                    return False
            return True
        
        return False
    
    def check_ship_endpoints(self, cluster):
        """Verifica che le estremità di una linea siano confermate come fine nave"""
        if len(cluster) <= 1:
            return True
        
        cluster.sort()
        start = cluster[0]
        end = cluster[-1]
        
        # Determina la direzione della linea
        if start[0] == end[0]:  # Orizzontale
            left = (start[0], start[1] - 1)
            right = (end[0], end[1] + 1)
            left_confirmed = (left[1] < 0 or left[1] >= GRID_SIZE or 
                            self.ai_shots[left[0]][left[1]] == MISS)
            right_confirmed = (right[1] < 0 or right[1] >= GRID_SIZE or 
                             self.ai_shots[right[0]][right[1]] == MISS)
            
            return left_confirmed and right_confirmed
            
        else:  # Verticale
            top = (start[0] - 1, start[1])
            bottom = (end[0] + 1, end[1])
            top_confirmed = (top[0] < 0 or top[0] >= GRID_SIZE or 
                           self.ai_shots[top[0]][top[1]] == MISS)
            bottom_confirmed = (bottom[0] < 0 or bottom[0] >= GRID_SIZE or 
                              self.ai_shots[bottom[0]][bottom[1]] == MISS)
            
            return top_confirmed and bottom_confirmed
        
    def get_ai_target(self):
        """Ottiene il prossimo target usando logica Prolog migliorata"""
        # Prima strategia: continua lungo la direzione di navi attive (non affondate)
        query = "continue_active_direction(X1, Y1, X2, Y2, X3, Y3)"
        try:
            result = list(self.prolog.query(query))
            if result:
                target = (result[0]['X3'], result[0]['Y3'])
                print(f"AI: Continuando nave attiva -> {target}")
                return target
        except Exception as e:
            print(f"Errore nella query direzione attiva: {e}")
            
        # Seconda strategia: colpisci celle adiacenti a hit attivi isolati
        query = "adjacent_to_isolated_hit(X1, Y1, X2, Y2)"
        try:
            result = list(self.prolog.query(query))
            if result:
                target = (result[0]['X2'], result[0]['Y2'])
                print(f"AI: Colpendo adiacente a hit isolato -> {target}")
                return target
        except Exception as e:
            print(f"Errore nella query hit isolato: {e}")
            
        # Terza strategia: continua da hit attivi isolati
        query = "continue_from_active_hit(X1, Y1, X2, Y2)"
        try:
            result = list(self.prolog.query(query))
            if result:
                target = (result[0]['X2'], result[0]['Y2'])
                print(f"AI: Continuando da hit attivo -> {target}")
                return target
        except Exception as e:
            print(f"Errore nella query continua hit attivo: {e}")
            
        # Quarta strategia: celle ad alta probabilità (lontane da navi affondate)
        query = "high_probability_cell(X, Y)"
        try:
            results = list(self.prolog.query(query))
            if results:
                choice = random.choice(results)
                target = (choice['X'], choice['Y'])
                print(f"AI: Cella alta probabilità -> {target}")
                return target
        except Exception as e:
            print(f"Errore nella query alta probabilità: {e}")
            
        # Strategia di fallback: qualsiasi cella valida
        query = "can_shoot(X, Y)"
        try:
            results = list(self.prolog.query(query))
            if results:
                choice = random.choice(results)
                target = (choice['X'], choice['Y'])
                print(f"AI: Colpo casuale -> {target}")
                return target
        except Exception as e:
            print(f"Errore nella query casuale: {e}")
            
        # Ultimo fallback
        for i in range(GRID_SIZE):
            for j in range(GRID_SIZE):
                if self.ai_shots[i][j] == WATER:
                    print(f"AI: Ultimo fallback -> ({i}, {j})")
                    return (i, j)
                    
        return None
        
    def check_winner(self):
        # Controlla se tutte le navi del giocatore sono affondate
        player_ships = sum(row.count(SHIP) for row in self.player_grid)
        if player_ships == 0:
            self.winner = "AI"
            self.game_state = "game_over"
            
        # Controlla se tutte le navi dell'AI sono affondate
        ai_ships = sum(row.count(SHIP) for row in self.ai_grid)
        if ai_ships == 0:
            self.winner = "Player"
            self.game_state = "game_over"
            
    def draw_grid(self, grid, shots_grid, offset_x, offset_y, show_ships=True):
        """Disegna una griglia"""
        for i in range(GRID_SIZE):
            for j in range(GRID_SIZE):
                x = offset_x + j * (CELL_SIZE + MARGIN)
                y = offset_y + i * (CELL_SIZE + MARGIN)
                
                color = LIGHT_GRAY
                
                if shots_grid[i][j] == HIT:
                    color = RED
                elif shots_grid[i][j] == MISS:
                    color = BLUE
                elif show_ships and grid[i][j] == SHIP:
                    color = GREEN
                elif grid[i][j] == HIT:
                    color = RED
                    
                pygame.draw.rect(self.screen, color, (x, y, CELL_SIZE, CELL_SIZE))
                pygame.draw.rect(self.screen, BLACK, (x, y, CELL_SIZE, CELL_SIZE), 1)
                
                
    def draw_ui(self):
        """Disegna l'interfaccia utente"""
        player_title = self.font.render("La tua flotta", True, BLACK)
        ai_title = self.font.render("Flotta nemica", True, BLACK)
        
        self.screen.blit(player_title, (50, 10))
        self.screen.blit(ai_title, (GRID_WIDTH + 100, 10))
        
        # Istruzioni basate sullo stato del gioco
        if self.game_state == "placing":
            if self.current_ship < len(self.ship_sizes):
                ship_size = self.ship_sizes[self.current_ship]
                instruction = f"Piazza nave di dimensione {ship_size} ({self.ship_orientation})"
                instruction_text = self.font.render(instruction, True, BLACK)
                self.screen.blit(instruction_text, (50, GRID_HEIGHT + 70))
                
                rotate_text = self.font.render("Premi R per ruotare", True, BLACK)
                self.screen.blit(rotate_text, (50, GRID_HEIGHT + 100))
        elif self.game_state == "playing":
            turn_text = "Il tuo turno" if self.player_turn else "Turno dell'AI"
            turn_surface = self.font.render(turn_text, True, BLACK)
            self.screen.blit(turn_surface, (50, GRID_HEIGHT + 70))
        elif self.game_state == "game_over":
            winner_text = f"Vince: {self.winner}!"
            winner_surface = self.big_font.render(winner_text, True, RED)
            text_rect = winner_surface.get_rect(center=(SCREEN_WIDTH // 2, GRID_HEIGHT + 100))
            self.screen.blit(winner_surface, text_rect)
            
    def run(self):
        running = True
        
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                    
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_r and self.game_state == "placing":
                        self.ship_orientation = "vertical" if self.ship_orientation == "horizontal" else "horizontal"
                        
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 1:  # Click sinistro
                        if self.game_state == "placing":
                            self.handle_player_placement(event.pos)
                        elif self.game_state == "playing" and self.player_turn:
                            self.handle_player_shot(event.pos)
                            
            # Turno dell'AI
            if self.game_state == "playing" and not self.player_turn:
                pygame.time.wait(500)
                self.ai_turn()
            
            self.screen.fill(WHITE)
            self.draw_grid(self.player_grid, self.ai_shots, 50, 50, show_ships=True)
            self.draw_grid(self.ai_grid, self.player_shots, GRID_WIDTH + 100, 50, show_ships=False)
            self.draw_ui()
            
            pygame.display.flip()
            self.clock.tick(60)
            
        pygame.quit()
        sys.exit()

if __name__ == "__main__":
    try:
        game = BattleshipGame()
        game.run()
    except ImportError:
        print("Errore: pyswip non trovato.")
    except Exception as e:
        print(f"Errore durante l'avvio del gioco: {e}")