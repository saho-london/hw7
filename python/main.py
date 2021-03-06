#!/usr/bin/env python
# -*- coding: utf-8 -*-

import copy
import json
import logging
import random
import webapp2
import numpy as np

# http://uguisu.skr.jp/othello/5-1.html
CORNER = 150.0
WALL = 0.5
WALLIN = 0.2
NXCORNER_OUT = -24.0
NXCORNER_IN = -28.0
NXWALL = -2.0
NXWALLCO = -1.8
INLAND = -0.4
INLANDCORNER = -0.0

LUT = {(1,1): CORNER, (1,2): NXCORNER_OUT, (1,3): WALL, (1,4): WALLIN, (1,5): WALLIN, (1,6): WALL, (1,7): NXCORNER_OUT, (1,8): CORNER,
        (2,1): NXCORNER_OUT, (2,2): NXCORNER_IN, (2,3): NXWALLCO, (2,4): NXWALL, (2,5): NXWALL, (2,6): NXWALLCO, (2,7): NXCORNER_IN, (2,8): NXCORNER_OUT,
        (3,1): WALL, (3,2): NXWALLCO, (3,3): INLANDCORNER, (3,4): INLAND, (3,5): INLAND, (3,6): INLANDCORNER, (3,7): NXWALLCO, (3,8): WALL,
        (4,1): WALLIN, (4,2): NXWALL, (4,3): INLAND, (4,4): INLAND, (4,5): INLAND, (4,6): INLAND, (4,7): NXWALL, (4,8): WALLIN,
        (5,1): WALLIN, (5,2): NXWALL, (5,3): INLAND, (5,4): INLAND, (5,5): INLAND, (5,6): INLAND, (5,7): NXWALL, (5,8): WALLIN,
        (6,1): WALL, (6,2): NXWALLCO, (6,3): INLANDCORNER, (6,4): INLAND, (6,5): INLAND, (6,6): INLANDCORNER, (6,7): NXWALLCO, (6,8): WALL,
        (7,1): NXCORNER_OUT, (7,2): NXCORNER_IN, (7,3): NXWALLCO, (7,4): NXWALL, (7,5): NXWALL, (7,6): NXWALLCO, (7,7): NXCORNER_IN, (7,8): NXCORNER_OUT,
        (8,1): CORNER, (8,2): NXCORNER_OUT, (8,3): WALL, (8,4): WALLIN, (8,5): WALLIN, (8,6): WALL, (8,7): NXCORNER_OUT, (8,8): CORNER}

CORNERS = [[1,1], [1,8], [8,1], [8,8]]
WALLS = [[1,3], [1,4], [1,5], [1,6], [3,1], [3,8], [4,1], [4,8], [5,1], [5,8], [6,1], [6,8], [8,3], [8,4], [8,5], [8,6]]
INLANDS = [[3,3], [3,4], [3,5], [3,6], [4,3], [4,4], [4,5], [4,6], [5,3], [5,4], [5,5], [5,6], [6,3], [6,4], [6,5], [6,6]]
NXWALLS = [[2,3], [2,4], [2,5], [2,6], [3,2], [3,7], [4,2], [4,7], [5,2], [5,7], [6,2], [6,7], [7,3], [7,4], [7,5], [7,6]]
NXCORNERS = [[1,2], [1,7], [2,1], [2,2], [2,7], [2,8], [7,1], [7,2], [7,7], [7,8], [8,2], [8,7]]

# Reads json description of the board and provides simple interface.
class Game:
	# Takes json or a board directly.
	def __init__(self, body=None, board=None):
                if body:
		        game = json.loads(body)
                        self._board = game["board"]
                else:
                        self._board = board

	# Returns piece on the board.
	# 0 for no pieces, 1 for player 1, 2 for player 2.
	# None for coordinate out of scope.
	def Pos(self, x, y):
		return Pos(self._board["Pieces"], x, y)

	# Returns who plays next.
	def Next(self):
		return self._board["Next"]

	# Returns the array of valid moves for next player.
	# Each move is a dict
	#   "Where": [x,y]
	#   "As": player number
	def ValidMoves(self):
                moves = []

                for pos in CORNERS:
                    move = {"Where": pos,
                        "As": self.Next()}
                    if self.NextBoardPosition(move):
                        moves.append(move)
                for pos in WALLS:
                    move = {"Where": pos,
                            "As": self.Next()}
                    if self.NextBoardPosition(move):
                        moves.append(move)
                
                for pos in INLANDS:
                    move = {"Where": pos,
                            "As": self.Next()}
                    if self.NextBoardPosition(move):
                        moves.append(move)

                for pos in NXWALLS:
                    move = {"Where": pos,
                            "As": self.Next()}
                    if self.NextBoardPosition(move):
                        moves.append(move)

                for pos in NXCORNERS:
                    move = {"Where": pos,
                            "As": self.Next()}
                    if self.NextBoardPosition(move):
                        moves.append(move)
                return moves

	# Helper function of NextBoardPosition.  It looks towards
	# (delta_x, delta_y) direction for one of our own pieces and
	# flips pieces in between if the move is valid. Returns True
	# if pieces are captured in this direction, False otherwise.
	def __UpdateBoardDirection(self, new_board, x, y, delta_x, delta_y):
		player = self.Next()
		opponent = 3 - player
		look_x = x + delta_x
		look_y = y + delta_y
		flip_list = []
		while Pos(new_board, look_x, look_y) == opponent:
			flip_list.append([look_x, look_y])
			look_x += delta_x
			look_y += delta_y
		if Pos(new_board, look_x, look_y) == player and len(flip_list) > 0:
                        # there's a continuous line of our opponents
                        # pieces between our own pieces at
                        # [look_x,look_y] and the newly placed one at
                        # [x,y], making it a legal move.
			SetPos(new_board, x, y, player)
			for flip_move in flip_list:
				flip_x = flip_move[0]
				flip_y = flip_move[1]
				SetPos(new_board, flip_x, flip_y, player)
                        return True
                return False

	# Takes a move dict and return the new Game state after that move.
	# Returns None if the move itself is invalid.
	def NextBoardPosition(self, move):
		x = move["Where"][0]
		y = move["Where"][1]
                if self.Pos(x, y) != 0:
                        # x,y is already occupied.
                        return None
		new_board = copy.deepcopy(self._board)
                pieces = new_board["Pieces"]

		if not (self.__UpdateBoardDirection(pieces, x, y, 1, 0)
                        | self.__UpdateBoardDirection(pieces, x, y, 0, 1)
		        | self.__UpdateBoardDirection(pieces, x, y, -1, 0)
		        | self.__UpdateBoardDirection(pieces, x, y, 0, -1)
		        | self.__UpdateBoardDirection(pieces, x, y, 1, 1)
		        | self.__UpdateBoardDirection(pieces, x, y, -1, 1)
		        | self.__UpdateBoardDirection(pieces, x, y, 1, -1)
		        | self.__UpdateBoardDirection(pieces, x, y, -1, -1)):
                        # Nothing was captured. Move is invalid.
                        return None
                
                # Something was captured. Move is valid.
                new_board["Next"] = 3 - self.Next()
		return Game(board=new_board)

        def Count(self):
            count = [0, 0, 0]

            for line in self._board["Pieces"]:
                for piece in line:
                    count[piece] = count[piece] + 1 

            return count

        def CountCorner(self):
            count = [0, 0, 0]

            count[self._board["Pieces"][0][0]] = count[self._board["Pieces"][0][0]] + 1;
            count[self._board["Pieces"][0][7]] = count[self._board["Pieces"][0][7]] + 1;
            count[self._board["Pieces"][7][0]] = count[self._board["Pieces"][7][0]] + 1;
            count[self._board["Pieces"][7][7]] = count[self._board["Pieces"][7][7]] + 1;

            return count

        def Score(self):
            score = 0;
            
            for x, line in enumerate(self._board["Pieces"]):
                for y, piece in enumerate(line):
                    if piece == 1:
                        score = score + LUT[(x + 1,y + 1)]
                    if piece == 2:
                        score = score - LUT[(x + 1,y + 1)]
            
            count = self.Count()

            if count[1] == 1:
                score = score - 200
            elif count[1] == 2:
                score = score - 50
            if self.Count()[2] == 1:
                score = score + 200
            elif count[2] == 2:
                score = score + 50

            return score


# Returns piece on the board.
# 0 for no pieces, 1 for player 1, 2 for player 2.
# None for coordinate out of scope.
#
# Pos and SetPos takes care of converting coordinate from 1-indexed to
# 0-indexed that is actually used in the underlying arrays.
def Pos(board, x, y):
	if 1 <= x and x <= 8 and 1 <= y and y <= 8:
		return board[y-1][x-1]
	return None

# Set piece on the board at (x,y) coordinate
def SetPos(board, x, y, piece):
	if x < 1 or 8 < x or y < 1 or 8 < y or piece not in [0,1,2]:
		return False
	board[y-1][x-1] = piece

# Debug function to pretty print the array representation of board.
def PrettyPrint(board, nl="<br>"):
	s = ""
	for row in board:
		for piece in row:
			s += str(piece)
		s += nl
	return s

def PrettyMove(move):
	m = move["Where"]
	return '%s%d' % (chr(ord('A') + m[0] - 1), m[1])

def ScoreRec(g, limit, alpha, beta):
        valid_moves = g.ValidMoves()
        length = len(valid_moves)
        limit = limit - length / 2.0

        if limit <= 0:
            return g.Score()

        count = g.Count()

        if count[0] == 0:
            if count[1] > count[2]:
                return float("inf")
            elif count[1] < count[2]:
                return -1 * float("inf")
            else:
                return 0

        if count[1] == 0:
            return -1 * float("inf")
        if count[2] == 0:
            return float("inf")

        player = g.Next()
        count = g.Count()

        if length == 0:
            if player == 1:
                return -1 * float("inf")
            if player == 2:
                return float("inf")

        for move in valid_moves:
            next_g = g.NextBoardPosition(move)
            score = ScoreRec(next_g, limit - 1, alpha, beta)

            if player == 1:
                if score > alpha:
                    alpha = score
            if player == 2:
                if  score < beta:
                    beta = score

            if alpha >= beta:
                break

        if player == 1:
            return alpha
        else:
            return beta


def FirstPhase(g):
        print("Check Valid Moves")
        valid_moves = g.ValidMoves()
        next_move = valid_moves[0]
        player = g.Next()

        if player == 1:
            best = -1 * float("inf")
        if player == 2:
            best = float("inf")

        alpha = -1 * float("inf")
        beta = float("inf")

        limit = 18

        length = len(valid_moves)

        limit = limit - length / 2.0

        # limit = len(valid_moves)

        for move in valid_moves:
            next_g = g.NextBoardPosition(move)
            score = ScoreRec(next_g, limit, alpha, beta)
            if player == 1:
                if score > alpha:
                    alpha = score
                    next_move = move
            if player == 2:
                if  score < beta:
                    beta = score
                    next_move = move
            if alpha >= beta:
                break

        return next_move
            
def MiddlePhase(g):
        valid_moves = g.ValidMoves()
        best = 64
        next_move = valid_moves[0]

        
        for move in valid_moves:
            next_g = g.NextBoardPosition(move)
            score = len(next_g.ValidMoves())
            if best > score:
                best = score
                next_move = move

        return next_move

def FinalPhase(g, alpha, beta):
        valid_moves = g.ValidMoves()
        player = g.Next()
        count = g.Count()

        if count[0] == 0:
            return (count[1] - count[2], None)

        if len(valid_moves) == 0:
            if player == 1:
                return (-64 , None)
            if player == 2:
                return (64 , None)
             

        next_move = valid_moves[0]
        if player == 1:
            best = -64
        if player == 2:
            best = 64

        for move in valid_moves:
            next_g = g.NextBoardPosition(move)
            score, nmove = FinalPhase(next_g, alpha, beta)
            if player == 1:
                if score > alpha:
                    alpha = score
                    next_move = move
            if player == 2:
                if  score < beta:
                    beta = score
                    next_move = move
            if alpha >= beta:
                break

        if player == 1:
            return (alpha, next_move)
        else:
            return (beta, next_move)

class MainHandler(webapp2.RequestHandler):
    # Handling GET request, just for debugging purposes.
    # If you open this handler directly, it will show you the
    # HTML form here and let you copy-paste some game's JSON
    # here for testing.
    def get(self):
        if not self.request.get('json'):
          self.response.write("""
<body><form method=get>
Paste JSON here:<p/><textarea name=json cols=80 rows=24></textarea>
<p/><input type=submit>
</form>
</body>
""")
          return
        else:
          g = Game(self.request.get('json'))
          self.pickMove(g)

    def post(self):
    	# Reads JSON representation of the board and store as the object.
    	g = Game(self.request.body)
        # Do the picking of a move and print the result.
        self.pickMove(g)

    def pickMove(self, g):
    	# Gets all valid moves.
    	valid_moves = g.ValidMoves()
    	if len(valid_moves) == 0:
    		# Passes if no valid moves.
    		self.response.write("PASS")
    	else:
    		# Chooses a valid move randomly if available.
                # TO STEP STUDENTS:
                # You'll probably want to change how this works, to do something
                # more clever than just picking a random move.
	    	# move = random.choice(valid_moves)
                count = g.Count()
                countC = g.CountCorner()
                if count[1] == 2 and count[2] == 2:
    		    self.response.write("D3")
                elif count[0] < 12 :
                    score, move = FinalPhase(g, 0, 64)
    		    self.response.write(PrettyMove(move))
                elif max(countC[1], countC[2]) >= 2:
                    move = MiddlePhase(g) 
    		    self.response.write(PrettyMove(move))
                else:
                    move = FirstPhase(g)
    		    self.response.write(PrettyMove(move))
app = webapp2.WSGIApplication([
    ('/', MainHandler)
], debug=True)
