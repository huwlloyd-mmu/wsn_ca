import simulation
import pygame
import ca
import sys
import numpy as np

screen_w = 800
screen_h = 300
font = None
small_font = None
med_font = None
screen = None
show_stencil = False

def debug_console(sim):
    command = input('debug command:')
    
    if 'debug_cell' in command:
        try:
            i_cell = int(command.split()[1])
            j_cell = int(command.split()[2])
            sim.set_debug_cell(i_cell, j_cell)
            print('set debug cell to',i_cell,j_cell)
        except:
            print('something went wrong')
    else:
        print('command not recognized')

def cell_in_stencil( sim, icell, jcell ):
    phase = sim.node_list[25].phase_count
    return ca.in_stencil( phase, icell, jcell )

def draw_label( text, x, y ):
    label = med_font.render(text, 0, (255,255,255))
    screen.blit( label, (x, y+200))

    
def draw_info_panel( sim ):
    draw_label( 'Movement', 25, 10 )
    draw_label( 'Ave', 125, 10)
    draw_label( 'Max', 125, 20)
    draw_label( 'Stop/start', 25, 40 )
    draw_label( 'Ave', 125, 40)
    draw_label( 'Max', 125, 50)
    
    move_ave = '{:f}'.format(sim.ave_dist)
    move_max = '{:f}'.format(sim.max_dist)
    draw_label( move_ave, 170, 10)
    draw_label( move_max, 170, 20)
    stop_ave = '{:f}'.format(sim.ave_stopstart)
    stop_max = '{:d}'.format(sim.max_stopstart)
    draw_label( stop_ave, 170, 40)
    draw_label( stop_max, 170, 50)

    draw_label( 'E (Comms)', 325, 10 )
    draw_label( 'Ave', 425, 10)
    draw_label( 'Max', 425, 20)
    draw_label( 'E (Movement)', 325, 40 )
    draw_label( 'Ave', 425, 40)
    draw_label( 'Max', 425, 50)
    draw_label( 'E (Total)', 325, 70 )
    draw_label( 'Ave', 425, 70)
    draw_label( 'Max', 425, 80)

    ec_ave = '{:f}'.format(sim.ave_e_comm)
    ec_max = '{:f}'.format(sim.max_e_comm)
    draw_label( ec_ave, 470, 10)
    draw_label( ec_max, 470, 20)

    em_ave = '{:f}'.format(sim.ave_e_move)
    em_max = '{:f}'.format(sim.max_e_move)
    draw_label( em_ave, 470, 40)
    draw_label( em_max, 470, 50)

    et_ave = '{:f}'.format(sim.ave_e_tot)
    et_max = '{:f}'.format(sim.max_e_tot)
    draw_label( et_ave, 470, 70)
    draw_label( et_max, 470, 80)

    phase_count = '{:d}'.format(sim.node_list[25].phase_count)
    draw_label( 'Phase', 600, 20)
    draw_label( phase_count, 650,20)

def draw_sim( sim ):
    pixels_per_m = min( screen_h/sim.h, screen_w / sim.w )
    sim_height_pixels = sim.h * pixels_per_m
    sim_width_pixels = sim.w * pixels_per_m
    sim_cell_size_pixels = sim.cell_size * pixels_per_m

    #draw the grid
    for i in range( int(sim_width_pixels//sim_cell_size_pixels)+1):
        x = i*sim_cell_size_pixels
        for j in range( int(sim_height_pixels//sim_cell_size_pixels)+1):
            y = j* sim_cell_size_pixels
            if (i+j)%2 == 1:
                pygame.draw.rect(screen, pygame.Color(32,32,32), pygame.Rect(x,y,sim_cell_size_pixels,sim_cell_size_pixels))

    #draw some lines every 5 cells (from the border up )
    y = 0
    while y < sim.h:
        pygame.draw.line( screen, pygame.Color(128, 0, 0), (0,sim_height_pixels-y*pixels_per_m), (sim_width_pixels,sim_height_pixels-y*pixels_per_m))  
        y += sim.cell_size*5
    x = 0
    while x < sim.w:
        pygame.draw.line( screen, pygame.Color(128, 0, 0), (x*pixels_per_m,sim_height_pixels), (x*pixels_per_m,0))  
        x += sim.cell_size*5
        
    #draw the barrier
    pygame.draw.line( screen, pygame.Color(255,255,255), (0,sim_height_pixels), (sim.w*pixels_per_m,sim_height_pixels) )
    #draw the nodes
    for n in sim.node_list:
        colour = (0,0,0)
        if len(sim.node_list[n].neighbors['C']) > 1:
            colour = (255,255,0)
        else:
            colour = (0,255,0)
        rectsize = 3
        pygame.draw.rect(screen,colour, pygame.Rect( sim.node_list[n].x*pixels_per_m-rectsize/2, sim_height_pixels - sim.node_list[n].y*pixels_per_m-rectsize/2, rectsize, rectsize))
        #label = small_font.render(str(sim.node_list[n].uid),0,(0,255,0))
        #screen.blit(label,(sim.node_list[n].x*pixels_per_m, sim.node_list[n].y*pixels_per_m))

    draw_info_panel( sim )

def write_stats( sim ): 
    print('dist {:f} moves {:f} e_comm {:f} e_move {:f} e_tot {:f} n_bar {:d}'.format(
        sim.ave_dist,sim.ave_stopstart*0.5,sim.ave_e_comm,sim.ave_e_move,sim.ave_e_tot,sim.count_barriers()))

def write_results( sim, file_name ):
    with open(file_name,'w') as out_file:
        out_file.write('width {:f} height {:f} delta {:f} n {:f} dense {:d} rs {:f} rc {:f} eps {:f}\n'.format(
            sim.w,sim.h,sim.cell_size,sim.num_nodes,sim.dense,sim.r_sense,sim.r_comm,sim.epsilon) )
        out_file.write('dist {:f} moves {:f} e_comm {:f} e_move {:f} e_tot {:f} n_bar {:d}\n'.format(
            sim.ave_dist,sim.ave_stopstart*0.5,sim.ave_e_comm,sim.ave_e_move,sim.ave_e_tot,sim.count_barriers()))
        out_file.write('final node positions\n')
        for n in sim.node_list:
            node = sim.node_list[n]
            out_file.write('{:f} {:f}\n'.format(node.x,node.y))

def run_graphical( sim ):
    global screen, font, small_font, med_font
    pygame.init()
    screen = pygame.display.set_mode( (screen_w, screen_h) )
    font = pygame.font.SysFont("monospace",20)
    small_font = pygame.font.SysFont("monospace",12)
    med_font = pygame.font.SysFont("monospace",14)

    paused = True

    #sim.step()
    single_step = False
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                break
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    exit() 
                elif event.key == pygame.K_p:
                    paused = not paused
                elif event.key == pygame.K_SPACE:
                    single_step = True
                elif event.key == pygame.K_d:
                    debug_console(sim)
     
        if not paused or single_step:
            done = sim.step()
            if done:
                print('done!')
        if sim.node_list[1].timer%100 == 0 and sim.node_list[1].timer != 0:
            single_step = False

        screen.fill((0,0,0))
        draw_sim(sim)
        pygame.display.flip()

'''
w, h : dimensions of ROI
rs, rc: sensing and communications radii
epsilon: position error
dense: True for dense deployment, False for random
'''  
w = 400
h = 100
rs = 5
epsilon = 1
rc = 30
num_trials = 50
dense = False
n_nodes = 350

sim = simulation.Simulation(n_nodes, w, h, rs, rc, epsilon, dense )
run_graphical(sim)

