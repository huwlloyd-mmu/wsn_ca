# cellular automaton for moving nodes

class CA:

    def in_stencil( self, phase_count ):
        return self.i_cell%3 == self.i_offs[phase_count%9] and self.j_cell%3 == self.j_offs[phase_count%9]

    def __init__( self, i_cell, j_cell ):
        self.i_offs = [0,1,2,0,1,2,0,1,2]
        self.j_offs = [0,0,0,1,1,1,2,2,2]
        self.dist_orders = {
            '+l' : ['N', 'NW', 'NE', 'E', 'C', 'W', 'SW', 'S', 'SE' ],
            '-l' : ['S', 'SE', 'SW', 'W', 'C', 'E', 'NE', 'N', 'NW' ],
            '+r' : ['N', 'NE', 'NW', 'W', 'C', 'E', 'SE', 'S', 'SW' ],
            '-r' : ['S', 'SW', 'SE', 'E', 'C', 'W', 'NW', 'N', 'NE' ] 
        }
        self.i_cell = i_cell
        self.j_cell = j_cell

    def step( self, state, phase_count, debug ):
        in_s = self.in_stencil( phase_count )
        if debug:
            print('ca: phase {:d} i_cell {:d} j_cell {:d} in {:b}'.format(phase_count,self.i_cell,self.j_cell,in_s)) 
        if not in_s:
            return None 

        total = 0
        for cell in state:
            total += state[cell]
        average = int(total / len(state))
        excess = total - len(state)*average

        changes = {}
        for cell in state:
            changes[cell] = average - state[cell]

        if self.j_cell%2 == 0:
            if average == 0:
                direction = '-l'
            else:
                direction = '+l'
        else:
            if average == 0:
                direction = '-r'
            else:
                direction = '+r'
        
        dist_order = self.dist_orders[direction]

        i = 0
        while excess > 0:
            if dist_order[i] in changes:
                changes[dist_order[i]] += 1
                excess -= 1
            i += 1
            
        return changes

