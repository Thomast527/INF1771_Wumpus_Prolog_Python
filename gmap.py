################################################
import pygame
import sys, time, random
from pyswip import Prolog, Functor, Variable, Query

import pathlib
current_path = str(pathlib.Path().resolve())

elapsed_time = 0
auto_play_tempo = 0.5
auto_play = True # desligar para controlar manualmente
show_map = False

scale = 60
size_x = 12
size_y = 12
width = size_x * scale  #Largura Janela
height = size_y * scale #Altura Janela

player_pos = (1,1,'norte')
energia = 100
pontuacao = 0


mapa=[['','','','','','','','','','','',''],
      ['','','','','','','','','','','',''],
      ['','','','','','','','','','','',''],
      ['','','','','','','','','','','',''],
      ['','','','','','','','','','','',''],
      ['','','','','','','','','','','',''],
      ['','','','','','','','','','','',''],
      ['','','','','','','','','','','',''],
      ['','','','','','','','','','','',''],
      ['','','','','','','','','','','',''],
      ['','','','','','','','','','','',''],
      ['','','','','','','','','','','','']]

visitados = []
certezas = []
breezes = set() # store the positions of breezes



pl_file = (current_path + '\\main.pl').replace('\\','/')
prolog = Prolog()
prolog.consult(pl_file)

last_action = ""


import heapq

def heuristic(a, b):
    # Manhattan distance
    return abs(a[0] - b[0]) + abs(a[1] - b[1])

def neighbours(x, y):
    moves = [(1,0), (-1,0), (0,1), (0,-1)] # right, left, up, down
    for dx,dy in moves:
        nx, ny = x+dx, y+dy 
        if 1 <= nx <= 12 and 1 <= ny <= 12: # within bounds
            yield (nx, ny) # return neighbor one by one if needed


def risk_cost(position):
    (x, y) = position
    # retriverd memory from Prolog
    memory = list(prolog.query(f"memory({x},{y},Z)"))
    if memory:
        # observations on this tile
        obs = list(memory[0]['Z'])
    else:
        obs = []

    # dangerous tile (passos/palmas)
    if 'passos' in obs or 'palmas' in obs:
        return float("inf")

    # tile already visited is safe
    if (x, y) in visitados:
        return 0

    # candidate pit tile
    if 'brisa' in obs:
        return 10_000   

    # safe tile
    return 1



from TreeNode import TreeNode
import heapq

def astar(start, goal, forbid_brisa=False):

    root = TreeNode(start, fx=heuristic(start, goal), gx=0)

    open_list = []
    heapq.heappush(open_list, root)

    best_node = { start: 0 }

    visited = set()

    while open_list:

        # We take the best node (lowest fx)
        current_node = heapq.heappop(open_list)
        current_node_x, current_node_y = current_node.get_coord()

        # If we've reached the goal, we reconstruct path
        if (current_node_x, current_node_y) == goal:
            path = []
            node = current_node
            while node is not None:
                path.append(node.get_coord())
                node = node.get_parent()
            return path[::-1]

        if (current_node_x, current_node_y) in visited:
            continue
        visited.add((current_node_x, current_node_y))

        for nx, ny in neighbours(current_node_x, current_node_y):

            memory = list(prolog.query(f"memory({nx},{ny},Z)"))
            observation = list(memory[0]['Z']) if memory else []

            
            if 'passos' in observation or 'palmas' in observation:
                continue

            if forbid_brisa and 'brisa' in observation:
                continue

            risk_cost_node = risk_cost((nx, ny))
            if risk_cost_node == float("inf"):
                continue

            tentative_g = current_node.get_value_gx() + 1 + risk_cost_node

            if (nx, ny) in best_node and tentative_g >= best_node[(nx, ny)]:
                continue

            best_node[(nx, ny)] = tentative_g

            f = heuristic((nx, ny), goal)

            child = TreeNode((nx, ny), fx=f, gx=tentative_g)
            child.set_parent(current_node)

            heapq.heappush(open_list, child)

    return None



caminho_retorno = []
index_retorno = 0


def direction_to_reach(direction_to_go):
    player_x, player_y, _ = player_pos
    desired_direction_x, desired_direction_y = direction_to_go

    if desired_direction_x == player_x+1: 
        return "leste"
    if desired_direction_x == player_x-1:
        return "oeste"
    if desired_direction_y == player_y+1: 
        return "norte"
    if desired_direction_y == player_y-1: 
        return "sul"
    return None

def turn_to(current_direction, desired_direction):
    """return "virar_direita" or "virar_esquerda" to go from current_direction to desired_direction"""

    directions_in_order = ["norte", "leste", "sul", "oeste"]
    current_direction_index = directions_in_order.index(current_direction)
    desired_direction_index = directions_in_order.index(desired_direction)

    if (current_direction_index + 1) % 4 == desired_direction_index:
        return "virar_direita"
    else:
        return "virar_esquerda"
    
    
def next_step():
    global index_retorno, caminho_retorno

    # end of path
    if caminho_retorno is None or caminho_retorno == [] or index_retorno >= len(caminho_retorno):
        return "sair"

    player_x, player_y, player_dir = player_pos
    next_pos = caminho_retorno[index_retorno]

    if (player_x, player_y) == next_pos:
        index_retorno += 1
        return next_step()

    desired_direction = direction_to_reach(next_pos)

    if desired_direction != player_dir:
        return turn_to(player_dir, desired_direction)

    index_retorno += 1
    return "andar"



EXPLORATION_MODE = False
current_path = [] 
path_step_index = 0 # from A*

def decisao():
    global caminho_retorno, index_retorno

    acoes = list(prolog.query("executa_acao(X)"))
    print(acoes)

    if not acoes:
        return ""

    acao = acoes[0]['X']


    if acao == "retornar":
        start = (player_pos[0], player_pos[1])
        goal = (1,1)

        caminho_retorno = astar(start, goal, forbid_brisa=True)
        index_retorno = 0

        if caminho_retorno:
            return next_step()

        caminho_retorno = astar(start, goal, forbid_brisa=False)
        index_retorno = 0

        if caminho_retorno:
            return next_step()

        return "virar_esquerda"


    if acao == "explorer":
        player_pos_x, player_pos_y, _ = player_pos

        safe = [] 
        unsafe = [] 

        for y in range(1, 13):
            for x in range(1,13):

                if (x,y) == (player_pos_x,player_pos_y):
                    continue
                if (x,y) in visitados:
                    continue

                memory = list(prolog.query(f"memory({x},{y},Z)"))
                if not memory:
                    continue

                observation = list(memory[0]['Z'])

                if "passos" in observation or "palmas" in observation:
                    continue    # dangerous

                if "brisa" in observation:
                    unsafe.append((x,y))
                else:
                    safe.append((x,y))


        if safe:
            start = (player_pos_x,player_pos_y)
            target = min(safe, key=lambda c: heuristic(start,c))

            caminho_retorno = astar(start, target, forbid_brisa=True)
            index_retorno = 0

            if caminho_retorno:
                return next_step()


            caminho_retorno = astar(start, target, forbid_brisa=False)
            index_retorno = 0
            return next_step()

        if unsafe:
            start = (player_pos_x,player_pos_y)
            target = min(unsafe, key=lambda c: heuristic(start,c))


            caminho_retorno = astar(start, target, forbid_brisa=False)
            index_retorno = 0

            if caminho_retorno:
                return next_step()


        return "virar_esquerda"

    return acao


def exec_prolog(a):
    global last_action
    if a == "sair":    # end of game
        last_action = a
        return
    if a != "":
        list(prolog.query(a))
    last_action = a


def update_prolog():
    global player_pos, mapa, energia, pontuacao,visitados, show_map, breezes

    list(prolog.query("atualiza_obs, verifica_player"))

    x = Variable()
    y = Variable()
    visitado = Functor("visitado", 2)
    visitado_query = Query(visitado(x,y))
    visitados.clear()
    while visitado_query.nextSolution():
        visitados.append((x.value,y.value))
    visitado_query.closeQuery()

    x = Variable()
    y = Variable()
    certeza = Functor("certeza", 2)
    certeza_query = Query(certeza(x,y))
    certezas.clear()
    while certeza_query.nextSolution():
        certezas.append((x.value,y.value))
    certeza_query.closeQuery()
        
    if show_map:    
        x = Variable()
        y = Variable()
        z = Variable()    
        tile = Functor("tile", 3)
        tile_query = Query(tile(x,y,z))
        while tile_query.nextSolution():
            mapa[y.get_value()-1][x.get_value()-1] = str(z.value)
        tile_query.closeQuery()

    else:

        y = 0
        for j in mapa:
            x = 0
            for i in j:
                mapa[y][x] = ''
                x  += 1
            y +=  1

        x = Variable()
        y = Variable()
        z = Variable()    
        memory = Functor("memory", 3)
        memory_query = Query(memory(x,y,z))

        breezes.clear()

        while memory_query.nextSolution():

            obs_list = list(z.value)  # liste des observations : ['brisa'], ['passos'], etc.

            # --- 1) MARQUER LES BRISES POUR LE COÛT DE RISQUE ---
            if "brisa" in obs_list:
                breezes.add((x.value, y.value))

            # --- 2) METTRE À JOUR LA CARTE (comme avant) ---
            for s in obs_list:
                s = str(s)
                if s == 'palmas':
                    mapa[y.get_value()-1][x.get_value()-1] += 'T'
                elif s == 'passos':
                    mapa[y.get_value()-1][x.get_value()-1] += 'D'
                elif s == 'reflexo':
                    mapa[y.get_value()-1][x.get_value()-1] += 'U'
                elif s == 'brilho':
                    mapa[y.get_value()-1][x.get_value()-1] += 'O'
                elif s == 'brisa':
                    mapa[y.get_value()-1][x.get_value()-1] += 'P'

        memory_query.closeQuery()


    x = Variable()
    y = Variable()
    z = Variable()

    posicao = Functor("posicao", 3)
    position_query = Query(posicao(x,y,z))
    position_query.nextSolution()
    player_pos = (x.value,y.value,str(z.value))
    position_query.closeQuery()

    x = Variable()
    energia = Functor("energia", 1)
    energia_query = Query(energia(x))
    energia_query.nextSolution()
    energia = x.value
    energia_query.closeQuery()

    x = Variable()
    pontuacao = Functor("pontuacao", 1)
    pontuacao_query = Query(pontuacao(x))
    pontuacao_query.nextSolution()
    pontuacao = x.value
    pontuacao_query.closeQuery()

    #print(mapa)
    #print(player_pos)


def load():
    global sys_font, clock, img_wall, img_grass, img_start, img_finish, img_path
    global img_gold,img_health, img_pit, img_bat, img_enemy1, img_enemy2,img_floor
    global bw_img_gold,bw_img_health, bw_img_pit, bw_img_bat, bw_img_enemy1, bw_img_enemy2,bw_img_floor
    global img_player_up, img_player_down, img_player_left, img_player_right, img_tomb

    sys_font = pygame.font.Font(pygame.font.get_default_font(), 20)
    clock = pygame.time.Clock() 

    img_wall = pygame.image.load('wall.jpg')
    #img_wall2_size = (img_wall.get_width()/map_width, img_wall.get_height()/map_height)
    img_wall_size = (width/size_x, height/size_y)
    
    img_wall = pygame.transform.scale(img_wall, img_wall_size)

    
    img_player_up = pygame.image.load('player_up.png')
    img_player_up_size = (width/size_x, height/size_y)
    img_player_up = pygame.transform.scale(img_player_up, img_player_up_size)

    img_player_down = pygame.image.load('player_down.png')
    img_player_down_size = (width/size_x, height/size_y)
    img_player_down = pygame.transform.scale(img_player_down, img_player_down_size)

    img_player_left = pygame.image.load('player_left.png')
    img_player_left_size = (width/size_x, height/size_y)
    img_player_left = pygame.transform.scale(img_player_left, img_player_left_size)

    img_player_right = pygame.image.load('player_right.png')
    img_player_right_size = (width/size_x, height/size_y)
    img_player_right = pygame.transform.scale(img_player_right, img_player_right_size)


    img_tomb = pygame.image.load('tombstone.png')
    img_tomb_size = (width/size_x, height/size_y)
    img_tomb = pygame.transform.scale(img_tomb, img_tomb_size)



    img_grass = pygame.image.load('grass.jpg')
    img_grass_size = (width/size_x, height/size_y)
    img_grass = pygame.transform.scale(img_grass, img_grass_size)

    img_floor = pygame.image.load('floor.png')
    img_floor_size = (width/size_x, height/size_y)
    img_floor = pygame.transform.scale(img_floor, img_floor_size)

    img_gold = pygame.image.load('gold.png')
    img_gold_size = (width/size_x, height/size_y)
    img_gold = pygame.transform.scale(img_gold, img_gold_size)

    img_pit = pygame.image.load('pit.png')
    img_pit_size = (width/size_x, height/size_y)
    img_pit = pygame.transform.scale(img_pit, img_pit_size)

    img_enemy1 = pygame.image.load('enemy1.png')
    img_enemy1_size = (width/size_x, height/size_y)
    img_enemy1 = pygame.transform.scale(img_enemy1, img_enemy1_size)

    img_enemy2 = pygame.image.load('enemy2.png')
    img_enemy2_size = (width/size_x, height/size_y)
    img_enemy2 = pygame.transform.scale(img_enemy2, img_enemy2_size)

    img_bat = pygame.image.load('bat.png')
    img_bat_size = (width/size_x, height/size_y)
    img_bat = pygame.transform.scale(img_bat, img_bat_size)

    img_health = pygame.image.load('health.png')
    img_health_size = (width/size_x, height/size_y)
    img_health = pygame.transform.scale(img_health, img_health_size)    
    
    bw_img_floor = pygame.image.load('bw_floor.png')
    bw_img_floor_size = (width/size_x, height/size_y)
    bw_img_floor = pygame.transform.scale(bw_img_floor, bw_img_floor_size)

    bw_img_gold = pygame.image.load('bw_gold.png')
    bw_img_gold_size = (width/size_x, height/size_y)
    bw_img_gold = pygame.transform.scale(bw_img_gold, bw_img_gold_size)

    bw_img_pit = pygame.image.load('bw_pit.png')
    bw_img_pit_size = (width/size_x, height/size_y)
    bw_img_pit = pygame.transform.scale(bw_img_pit, bw_img_pit_size)

    bw_img_enemy1 = pygame.image.load('bw_enemy1.png')
    bw_img_enemy1_size = (width/size_x, height/size_y)
    bw_img_enemy1 = pygame.transform.scale(bw_img_enemy1, bw_img_enemy1_size)

    bw_img_enemy2 = pygame.image.load('bw_enemy2.png')
    bw_img_enemy2_size = (width/size_x, height/size_y)
    bw_img_enemy2 = pygame.transform.scale(bw_img_enemy2, bw_img_enemy2_size)

    bw_img_bat = pygame.image.load('bw_bat.png')
    bw_img_bat_size = (width/size_x, height/size_y)
    bw_img_bat = pygame.transform.scale(bw_img_bat, bw_img_bat_size)

    bw_img_health = pygame.image.load('bw_health.png')
    bw_img_health_size = (width/size_x, height/size_y)
    bw_img_health = pygame.transform.scale(bw_img_health, bw_img_health_size)  

def update(dt, screen):
    
    global elapsed_time
    
    elapsed_time += dt
    
    if (elapsed_time / 1000) > auto_play_tempo:
        
        if auto_play and player_pos[2] != 'morto':
            exec_prolog(decisao())
            update_prolog()
       
        elapsed_time = 0
        
    

def key_pressed(event):
    
    global show_map
    #leitura do teclado
    if event.type == pygame.KEYDOWN:
        
        if not auto_play and player_pos[2] != 'morto':
            if event.key == pygame.K_LEFT: #tecla esquerda
                exec_prolog("virar_esquerda")
                update_prolog()

            elif event.key == pygame.K_RIGHT: #tecla direita
                exec_prolog("virar_direita")
                update_prolog()

            elif event.key == pygame.K_UP: #tecla  cima
                exec_prolog("andar")
                update_prolog()

            if event.key == pygame.K_SPACE:
                exec_prolog("pegar")
                update_prolog()
    
        if event.key == pygame.K_m:
            show_map = not show_map
            update_prolog()


def draw_screen(screen):
    
    screen.fill((0,0,0))
 
    y = 0
    for j in mapa:
        x = 0
        for i in j:

            if (x+1,12-y) in visitados:
                screen.blit(img_floor, (x * img_floor.get_width(), y * img_floor.get_height()))
            else:
                screen.blit(bw_img_floor, (x * bw_img_floor.get_width(), y * bw_img_floor.get_height()))

            if mapa[11-y][x].find('P') > -1:
                if (x+1,12-y) in certezas:
                    screen.blit(img_pit, (x * img_pit.get_width(), y * img_pit.get_height()))                            
                else:
                    screen.blit(bw_img_pit, (x * bw_img_pit.get_width(), y * bw_img_pit.get_height()))                            

            if mapa[11-y][x].find('T') > -1:
                if (x+1,12-y) in certezas:
                    screen.blit(img_bat, (x * img_bat.get_width(), y * img_bat.get_height()))
                else:
                    screen.blit(bw_img_bat, (x * bw_img_bat.get_width(), y * bw_img_bat.get_height()))

            if mapa[11-y][x].find('D') > -1:
                if (x+1,12-y) in certezas:
                    screen.blit(img_enemy1, (x * img_enemy1.get_width(), y * img_enemy1.get_height()))                                               
                else:
                    screen.blit(bw_img_enemy1, (x * bw_img_enemy1.get_width(), y * bw_img_enemy1.get_height()))                                               
                            
            if mapa[11-y][x].find('d') > -1:
                if (x+1,12-y) in certezas:
                    screen.blit(img_enemy2, (x * img_enemy2.get_width(), y * img_enemy2.get_height()))                                               
                else:
                    screen.blit(bw_img_enemy2, (x * bw_img_enemy2.get_width(), y * bw_img_enemy2.get_height()))                                               

            if mapa[11-y][x].find('U') > -1:
                if (x+1,12-y) in certezas:
                    screen.blit(img_health, (x * img_health.get_width(), y * img_health.get_height()))                               
                else:
                    screen.blit(bw_img_health, (x * bw_img_health.get_width(), y * bw_img_health.get_height()))                               

            if mapa[11-y][x].find('O') > -1:
                if (x+1,12-y) in certezas:
                    screen.blit(img_gold, (x * img_gold.get_width(), y * img_gold.get_height()))                
                else:
                    screen.blit(bw_img_gold, (x * bw_img_gold.get_width(), y * bw_img_gold.get_height()))                
            
            if x == player_pos[0] - 1  and  y == 12 - player_pos[1]:
                if player_pos[2] == 'norte':
                    screen.blit(img_player_up, (x * img_player_up.get_width(), y * img_player_up.get_height()))                                               
                elif player_pos[2] == 'sul':
                    screen.blit(img_player_down, (x * img_player_down.get_width(), y * img_player_down.get_height()))                                               
                elif player_pos[2] == 'leste':
                    screen.blit(img_player_right, (x * img_player_right.get_width(), y * img_player_right.get_height()))                                               
                elif player_pos[2] == 'oeste':
                    screen.blit(img_player_left, (x * img_player_left.get_width(), y * img_player_left.get_height()))                                                                                                           
                else:
                    screen.blit(img_tomb, (x * img_tomb.get_width(), y * img_tomb.get_height()))                                                                                                           
            x  += 1
        y +=  1

    t = sys_font.render("Pontuação: " + str(pontuacao), False, (255,255,255))
    screen.blit(t, t.get_rect(top = height + 5, left=40))

    t = sys_font.render(last_action, False, (255,255,255))
    screen.blit(t, t.get_rect(top = height + 5, left=width/2-40))
    
    t = sys_font.render("Energia: " + str(energia), False, (255,255,255))
    screen.blit(t, t.get_rect(top = height + 5, left=width-140))

def main_loop(screen):  
    global clock
    running = True
    
    while running:
        for e in pygame.event.get(): 
            if e.type == pygame.QUIT:
                running = False
                break
            
            key_pressed(e)
            
        # Calcula tempo transcorrido desde
        # a última atualização 
        dt = clock.tick()
        
        
        # Atualiza posição dos objetos da tela
        update(dt, screen)
        
        # Desenha objetos na tela 
        draw_screen(screen)

        # Pygame atualiza o seu estado
        pygame.display.update() 


update_prolog()

pygame.init()
pygame.display.set_caption('INF1771 Trabalho 2 - Agente Lógico')
screen = pygame.display.set_mode((width, height+30))
load()

main_loop(screen)
pygame.quit()



