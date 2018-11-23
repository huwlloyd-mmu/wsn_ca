import random
import math
import ca

class Node:
    def __init__( self, sim, x, y, uid, r_sense, r_comm, w, h, cell_size ):
        self.sim = sim  # the simulation object, use this for sending messages
        self.x = x      # x position
        self.y = y      # y position
        self.uid = uid  # unique identifier (int)
        self.r_sense = r_sense # sensing radius
        self.r_comm = r_comm # communication radius
        self.state = 'start' # state machine has four states - start, moving, idle, run_ca
        self.w = w      # width of deployment region
        self.h = h      # height of deployment region
        self.cell_size = cell_size # width/height of the (square) cells
        self.num_stops = 0
        self.num_starts = 0
        self.distance_moved = 0
        self.messages_sent = 0
        self.messages_recv = 0
        self.comms_energy = 0
        self.movement_energy = 0
        self.timer = 0
        self.phase_count = 0
        self.no_move_phases = 0
        self.init_cell_info()
        self.phase_period = 100
        self.since_move = 0
        self.message_queue = []
        
    def update_start( self ):
        # all we need to do here is send a message advertising our position
        i = self.x // self.cell_size
        j = self.y // self.cell_size
        # on the grid
        self.broadcast_position()
        self.state = 'idle'

        
    def pick_point_in_cell( self, i, j, relative ):
        # returns a target point in the given cell (i, j, and relative)
        # e.g. 3, 4, 'W' is 2, 4.
        # position returned is the centre of the cell
        i_target = i
        j_target = j

        if 'N' in relative:
            j_target += 1
        if 'S' in relative:
            j_target -= 1
        if 'E' in relative:
            i_target += 1
        if 'W' in relative:
            i_target -= 1

        x0 = i_target * self.cell_size
        y0 = j_target * self.cell_size
        x1 = x0 + self.cell_size
        y1 = y0 + self.cell_size
        x_target = (x0+x1)*0.5
        y_target = (y0+y1)*0.5
        # clamp to the ROI
        x_target = min(max(x_target,0.0),self.w)
        y_target = min(max(y_target,0.0),self.h)
        return (x_target, y_target)

    def move_to_barrier_pos( self ):
        # move to final position in the centre of the cell.
        d_cell = self.cell_size
        x_barrier = (self.i_cell + 0.5) * d_cell
        y_barrier = (self.j_cell + 0.5)* d_cell 
        if (self.x-x_barrier)**2 + (self.y-y_barrier)**2 > 1e-4:
            self.move_to(x_barrier, y_barrier)

    def update_run_ca( self ):
        # run the cellular automaton to decide what to do
        self.state = 'idle' # return to idle immediately after this
        self.since_move += 1 # increment the number of phases since a move
        debug_this = False
        if self.sim.debug_cell != None:
            if self.i_cell == self.sim.debug_cell[0] and self.j_cell == self.sim.debug_cell[1] and self.uid == max( [c[0] for c in self.neighbors['C']] ):
                debug_this = True
        ca_state = {}
        for c in self.neighbors:
            ca_state[c] = len(self.neighbors[c])
        self.phase_count = self.timer//self.phase_period

        num_x = int(math.ceil(self.w / (self.cell_size)))
        num_y = int(math.ceil(self.h / (self.cell_size)))

        ca_result = self.ca.step( ca_state, self.phase_count, debug_this ) #ca.ca_step( ca_state, self.i_cell, self.j_cell, self.phase_count, num_per_cell, num_x, num_y, debug_this )
        if debug_this:
            print('new phase',self.phase_count,'for',self.uid,self.x,self.y,self.i_cell,self.j_cell)
            print('neighbors',self.neighbors)
            print('cluster counts:',[(c,len(self.neighbors[c])) for c in self.neighbors])
            print('phase',self.phase_count,'ca_result',ca_result)
        if ca_result == None:
            # do nothing, wait for next phase
            return
        else:
            # redistribute the nodes
            move_list = []
            offsets = {'C':(0,0), 'W':(-1,0), 'E':(1,0), 'N':(0,1), 'S':(0,-1), 'SE':(1,-1), 'SW':(-1,-1), 'NE':(1,1), 'NW':(-1,1)}
            '''
            # move by taking nodes from cells with excesses into cells with deficits
            for c in ca_result:
                if ca_result[c] < 0:
                    # we need to move some out of this cell
                    # find a positive cell to move to
                    for c2 in ca_result:
                        if c2 != c:
                            while ca_result[c] < 0 and ca_result[c2] > 0:
                                # move here
                                move_list.append( (c,c2) )
                                ca_result[c2] -= 1
                                ca_result[c] += 1

            '''
            # move by taking nodes from cells with excesses into cells with deficits
            for c in ca_result:
                while ca_result[c] < 0:
                    # we need to move some out of this cell
                    # find nearest positive cell to move to
                    near_dist = 1000
                    near = None
                    for c2 in ca_result:
                        if c2 != c and ca_result[c2] > 0:
                            dist = (offsets[c][0] - offsets[c2][0])**2 + (offsets[c][1] - offsets[c2][1])**2
                            if dist < near_dist:
                                near_dist = dist
                                near = c2
                    if near != None:
                        move_list.append( (c,near) )
                        ca_result[near] -= 1
                        ca_result[c] += 1
                        
            # are we responsible for sending move messages?
            messenger = self.uid == max( [c[0] for c in self.neighbors['C']] )
            # now figure out which cells do the moving
            # for now use the uids in sorted order
            

            index = { 'C' : 0, 'W' : 0, 'E' : 0, 'S' : 0, 'N': 0, 'SW' : 0, 'NW' : 0, 'SE' : 0, 'NE' : 0  }
            if debug_this:
                print('moves',move_list, 'messenger', messenger)
            if len(move_list) == 0: # check whether to move to the final barrier position
                self.no_move_phases += 1
                if self.no_move_phases > 1 and len(self.neighbors['C']) == 1:
                    self.move_to_barrier_pos()
            else:
                self.no_move_phases = 0
                for move in move_list:
                    cluster0 = move[0]
                    uid0 = sorted(self.neighbors[cluster0])[index[cluster0]][0]
                    index[cluster0] += 1
                    x, y = self.pick_point_in_cell( self.i_cell, self.j_cell, move[1] )
                    if debug_this:
                        print('move',uid0,'to',x,y,'(',move[1],')')
                    if uid0 == self.uid or messenger:
                        # move this node to a new cell
                        self.sim.send_message( { 'message_id' : 'move', 'sender_uid' : self.uid, 'destination' : uid0, 'x' : x, 'y' : y } )
            
    def update_idle( self ):
        self.handle_messages()
        if self.timer%self.phase_period == 0:
            self.state = 'run_ca'


    def update_moving( self ):
        if self.new_move_phase:
            # tell anyone who is listening that we are no longer valid in any of their lists
            message = { 'message_id' : 'leave', 'sender_uid' : self.uid, 'destination' : 'any', 'uid': self.uid }
            self.send_message(message)
            self.new_move_phase = False

        # move at constant speed towards the target
        epsilon = 1e-4
        speed = 0.2 # 0.1m per update
        if (self.x - self.x_target)**2 + (self.y - self.y_target)**2 < epsilon**2:
            # we have arrived, send arrival message and set state back to idle
            self.x = self.x_target
            self.y = self.y_target
            self.i_cell = self.x // self.cell_size
            self.j_cell = self.y // self.cell_size
            self.state = 'idle'
            self.init_cell_info() # clear cluster info. This will get filled in by incoming messages
            self.broadcast_position()
        else:
            dx = self.x_target - self.x
            dy = self.y_target - self.y
            distance = math.sqrt(dx*dx + dy*dy)
            if distance > speed:
                dx *= speed/distance
                dy *= speed/distance
            self.x += dx
            self.y += dy
            
    def update( self ):
        # step the simulations
        self.timer += 1

        if self.state == 'redundant':
            return
        elif self.state == 'start':
            self.update_start()
        elif self.state == 'moving':
            self.update_moving()
        elif self.state == 'run_ca':
            self.update_run_ca()
        else:
            self.update_idle()

    def init_cell_info( self ):
        # info on neighbors - this one, and neighbours, stored in a dictionary of lists
        # neighbors are a list of nodes represented as tuples - (uid, x, y)
        self.i_cell = int(self.x / self.cell_size)
        self.j_cell = int(self.y / self.cell_size)

        self.neighbors = { 'C' : [ (self.uid, self.x, self.y) ] }
        # dictionary for finding neighbors relative to this one
        num_x_cells = int(math.ceil(self.w / (self.cell_size)))
        num_y_cells = int(math.ceil(self.h / (self.cell_size)))

        self.cell_lookup = {}
        self.cell_lookup[(self.i_cell, self.j_cell)] = 'C'

        if self.i_cell > 0:
            self.cell_lookup[(self.i_cell-1, self.j_cell)] = 'W'
            self.neighbors['W'] = []
        if self.i_cell < num_x_cells-1:
            self.cell_lookup[(self.i_cell+1, self.j_cell)] = 'E'
            self.neighbors['E'] = []
        if self.j_cell > 0:
            self.cell_lookup[(self.i_cell, self.j_cell-1)] = 'S'
            self.neighbors['S'] = []
        if self.j_cell < num_y_cells-1:
            self.cell_lookup[(self.i_cell, self.j_cell+1)] = 'N'
            self.neighbors['N'] = []

        if self.i_cell > 0 and self.j_cell > 0:
            self.cell_lookup[(self.i_cell-1, self.j_cell-1)] = 'SW'
            self.neighbors['SW'] = []
        if self.i_cell > 0 and self.j_cell < num_y_cells-1:
            self.cell_lookup[(self.i_cell-1, self.j_cell+1)] = 'NW'
            self.neighbors['NW'] = []
        if self.i_cell < num_x_cells-1 and self.j_cell > 0:
            self.cell_lookup[(self.i_cell+1, self.j_cell-1)] = 'SE'
            self.neighbors['SE'] = []
        if self.i_cell < num_x_cells-1 and self.j_cell < num_y_cells-1:
            self.cell_lookup[(self.i_cell+1, self.j_cell+1)] = 'NE'
            self.neighbors['NE'] = []
        # initialise the cellular automaton (and throw away the old one)
        self.ca = ca.CA( self.i_cell, self.j_cell )

    def send_message( self, message ):
        if message['destination'] != self.uid: # allow to send messages to self for free
            self.messages_sent += 1
            self.comms_energy += 1.25
        self.sim.send_message(message)

    def broadcast_position( self ):
        # send a message to all nodes with position
        message_id = None
        if self.state == 'init':
            message_id = 'initial_pos'
        else:
            message_id = 'arrival'
        message = { 'message_id' : message_id, 'sender_uid' : self.uid, 'destination' : 'any', 'uid' : self.uid, 'x' : self.x, 'y' : self.y }
        self.send_message(message)

    def add_new_node( self, uid, x, y ):
        if uid == self.uid:
            return
        # find the cluster this position is in
        cluster_coords = ( int(x / self.cell_size), int(y / self.cell_size) )
        # add the node to the appropriate cluster, if it's not already there
        if cluster_coords in self.cell_lookup:
            entry = (uid, x, y) # uid, position coords
            cluster = self.cell_lookup[cluster_coords]
            if not uid in [c[0] for c in self.neighbors[cluster]]:
                self.neighbors[cluster].append(entry)

    def move_to( self, x, y ):
        self.x_target = x
        self.y_target = y
        self.state = 'moving'
        self.num_starts += 1
        self.num_stops += 1
        distance = math.sqrt( (self.x-self.x_target)**2 + (self.y-self.y_target)**2 )
        self.distance_moved += distance
        self.movement_energy += 1.125*(600 + 300*distance)
        self.new_move_phase = True # set this so we know to do any processing required at the start of the phase
        self.since_move = 0
        
    def receive_arrival_message( self, uid, x, y ):
        # receive a message from a node which has just completed a move
        # first check is this already in one of our cluster lists? If so, remove it
        # as it has now moved
        #if self.state == 'moving':
            # ignore if we are moving, when we stop and broadcast position
            # we will get everything we need to know
            #return
        if uid == self.uid:
            return
        for c in self.neighbors:
            found = None
            for n in self.neighbors[c]:
                if n[0] == uid:
                    found = n
            if found != None:
                self.neighbors[c].remove(found)

        # decide whether it is our responsibility to send this new node a message
        # we do this if we are in the same or neighbouring cluster to the new arrival, 
        cluster_coords = ( int(x / self.cell_size), int(y / self.cell_size) )
        send_message = False
        # send a welcome message if the new arrival is in this cell or its neighbours
        if cluster_coords in self.cell_lookup:
            message = { 'message_id' : 'welcome', 'sender_uid' : self.uid, 'destination' : uid, 'uid': self.uid, 'x': self.x, 'y' : self.y }
            self.send_message(message)
        # re-add the new node (in the right cluster this time)
        self.add_new_node(uid, x, y)

    def receive_initial_position_message( self, uid, x, y ):
        # receive a message from node id, advertising its position x, y
        if uid == self.uid:
            return
        self.add_new_node(uid, x, y)

    def receive_welcome_message( self, uid, x, y ):
        # receive a message from a cluster we have just arrived in (or its neighbours)
        if uid == self.uid:
            return
        self.add_new_node(uid, x, y)

    def receive_move_message( self, x, y ):
        # receive a message from another node, telling us to move to x, y
        self.move_to(x, y)

    def receive_leave_message( self, uid ):
        # this is a message from another node, saying it is about to leave its current cell
        # remove it from any of our lists
        if uid == self.uid:
            return
        for c in self.neighbors:
            found = None
            for n in self.neighbors[c]:
                if n[0] == uid:
                    found = n
            if found != None:
                self.neighbors[c].remove(found)
    def handle_message( self, message ):
        # a message is a dictionary
        if message['message_id'] == 'arrival':
            self.receive_arrival_message( message['uid'], message['x'], message['y'])
        elif message['message_id'] == 'initial_pos':
            self.receive_initial_position_message( message['uid'], message['x'], message['y'] )
        elif message['message_id'] == 'welcome':
            self.receive_welcome_message( message['uid'], message['x'], message['y'])
        elif message['message_id'] == 'leave':
            self.receive_leave_message( message['uid'] )
        elif message['message_id'] == 'move':
            self.receive_move_message( message['x'], message['y'] )

    def handle_messages( self ):
        for m in self.message_queue:
            self.handle_message(m)
        self.message_queue.clear()
        
    def receive_message( self, message ):
        if message['sender_uid'] != self.uid: 
            self.messages_recv += 1
            self.comms_energy += 1.0
        self.message_queue.append(message)

      
    def get_position( self ):
        return (self.x, self.y)
    
