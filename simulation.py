import random
import node
import collections
import math
import numpy as np

class Simulation:

    def __init__( self, num_nodes, w, h, r_sense, r_comm, epsilon, dense ):
        self.node_list = {} # actually a dictionary, indexed by uid
        uid = 1
        # work out how many barriers we will be able to produce
        self.cell_size = 2*r_sense - epsilon
        self.num_per_barrier = int(w / self.cell_size)
        self.num_barriers = num_nodes // self.num_per_barrier        
        self.num_per_barrier = num_nodes // self.num_barriers
      
        self.w = w
        self.h = h
        self.debug_cell = None

        self.num_nodes = num_nodes
        self.dense = dense
        self.r_sense = r_sense
        self.r_comm = r_comm
        self.epsilon = epsilon
        self.max_e_comm = 0
        self.max_e_move = 0
        self.max_e_tot = 0
        self.max_dist = 0
        self.max_stopstart = 0
        self.ave_e_comm = 0
        self.ave_e_move = 0
        self.ave_e_tot = 0
        self.ave_dist = 0
        self.ave_stopstart = 0
        
        for i in range(num_nodes):
            if dense:
                x = self.cell_size*random.random()
                y = self.cell_size*random.random()
            else:
                x = w*random.random()
                y = h*random.random()
            a_node = node.Node( self, x, y, uid, r_sense, r_comm, w, h, self.cell_size )
            self.node_list[uid] = a_node
            uid += 1
                
    def set_debug_cell( self, i, j ):
        self.debug_cell = (i,j)

    def send_message( self, message ):
        sender_uid = message['sender_uid']
        sender = self.node_list[sender_uid]
        #messages sent to a destination go only to that destination
        if message['destination'] == 'any':
            # find all the nodes within the sender's communication radius
            for n in self.node_list:
                if n != sender_uid and (self.node_list[n].x - sender.x)**2 + (self.node_list[n].y - sender.y)**2 < sender.r_comm*sender.r_comm:
                    # in range, send the message
                    self.node_list[n].receive_message( message )
        else:
            # send to a particular node, but it has to be in range
            other = self.node_list[message['destination']]
            if (other.x - sender.x)**2 + (other.y - sender.y)**2 < sender.r_comm*sender.r_comm:
                other.receive_message(message)
        
                            
    def calculate_energy_stats(self):
        self.tot_e_comm = 0
        self.tot_e_move = 0
        self.max_e_comm = 0
        self.max_e_move = 0
        self.max_e_tot = 0
        self.tot_dist = 0
        self.tot_stopstart = 0
        self.max_dist = 0
        self.max_stopstart = 0
        
        num_nodes = len(self.node_list)
        for c in self.node_list:
            n = self.node_list[c]

            self.tot_e_comm += n.comms_energy
            if n.comms_energy > self.max_e_comm:
                self.max_e_comm = n.comms_energy
    
            self.tot_e_move += n.movement_energy
            if n.movement_energy > self.max_e_move:
                self.max_e_move = n.movement_energy

            if n.movement_energy + n.comms_energy > self.max_e_tot:
                self.max_e_tot = n.movement_energy + n.comms_energy

            self.tot_dist += n.distance_moved
            if n.distance_moved > self.max_dist:
                self.max_dist = n.distance_moved

            self.tot_stopstart += n.num_stops+n.num_starts
            if n.num_stops+n.num_starts > self.max_stopstart:
                self.max_stopstart = n.num_stops + n.num_starts

        self.ave_e_comm = self.tot_e_comm / num_nodes
        self.ave_e_move = self.tot_e_move / num_nodes
        self.ave_e_tot = (self.tot_e_comm + self.tot_e_move)/ num_nodes
        self.ave_dist = self.tot_dist / num_nodes
        self.ave_stopstart = self.tot_stopstart/ num_nodes

    def step( self ):
        for n in self.node_list:
            self.node_list[n].update()
        self.calculate_energy_stats()
        return self.done()
        
    def done( self ):
        # check whether the simulation has stopped changing
        self.biggest_distance = 0.0
        self.smallest_since_move = 1000000000

        for n in self.node_list:
            if self.node_list[n].since_move < self.smallest_since_move:
                self.smallest_since_move = self.node_list[n].since_move
                
        return self.smallest_since_move > 100

    def count_barriers( self ):
        num_x_sites = self.w // self.cell_size
        num_y_sites = self.h // self.cell_size

        num_barriers = 0

        cells = np.full( (num_x_sites, num_y_sites), False, dtype=bool )
        
        for n in self.node_list:
            # find the nearest barrier point to this node
            x = self.node_list[n].x
            y = self.node_list[n].y

            i = int(x/self.cell_size)
            j = int(y/self.cell_size)

            x_site = (i+0.5)*self.cell_size
            y_site = (j+0.5)*self.cell_size

            epsilon = 2e-4
            if i >= 0 and i < num_x_sites and j >= 0 and j < num_y_sites:
                
                dist = (x-x_site)**2 + (y-y_site)**2
                if dist < epsilon:
                    cells[i][j] = True
        # now count barriers
        num_complete_barriers = 0
        for j in range(num_y_sites):
            all_filled = True
            for i in range(num_x_sites):
                if not cells[i][j]:
                    all_filled = False
                    break
            if all_filled:
                num_complete_barriers += 1
        return num_complete_barriers




    
