import simulation
import ca
import sys
import numpy as np


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

def run_text( sim ):
    i_step = 0
    done = False
    while not done:
        done = sim.step()
    write_stats(sim)

def run_experiment( w, h, rs, epsilon, rc, n_nodes, num_trials, dense, out_folder ): 
    moves = []
    dist = []
    e_comm = []
    e_tot = []
    e_move = []
    n_barriers = []

    for i in range(num_trials):
        sim = simulation.Simulation(n_nodes, w, h, rs, rc, epsilon, dense )
        filename = out_folder+'/'+'run{:d}.dat'.format(i)
        print('running',i)
        run_text(sim)
        moves.append(sim.ave_stopstart*0.5)
        dist.append(sim.ave_dist)
        e_comm.append(sim.ave_e_comm)
        e_move.append(sim.ave_e_move)
        e_tot.append(sim.ave_e_tot)
        n_barriers.append(sim.count_barriers())
        write_results(sim,filename)
        
    summary_string = 'Averages over {:d} runs \ndistance {:f} moves {:f} e_comm {:f} e_move {:f} e_tot {:f} num_barriers {:f}\n'.format(
           num_trials,np.mean(dist), np.mean(moves), np.mean(e_comm), np.mean(e_move), np.mean(e_tot), np.mean(n_barriers) )
    print(summary_string)

    summary_file = out_folder+'/'+'summary.dat'
    with open(summary_file,'w') as out_file:
        out_file.write(summary_string)

'''
Run to completion 50 times each for 50,100,150,...,350 nodes
w, h : dimensions of ROI
rs, rc: sensing and communications radii
epsilon: position error
dense: True for dense deployment, False for random

expects directories dense_50, dense_100,... random_350 to exist for results
'''

w = 400
h = 100
rs = 5
epsilon = 1
rc = 30
num_trials = 50
dense = True
directory_root = { True:'dense_', False:'random_' }

for n_nodes in [50,100,150,200,250,300,350]:
    out_dir = directory_root[dense].format(n_nodes)
    run_experiment( w, h, rs, epsilon, rc, n_nodes, num_trials, dense, out_dir )


