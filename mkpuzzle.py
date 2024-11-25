#
# Copyright 2024 Jeff Bush
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

import json
import sys

BLANK = '_'
clues = []
cross_lookup = {}

def init_cross_lookup():
    for word_index, (word, _) in enumerate(clues):
        for offset, letter in enumerate(word):
            if letter in cross_lookup:
                cross_lookup[letter].append((word_index, offset))
            else:
                cross_lookup[letter] = [(word_index, offset)]


def try_to_add_word(puzzle_data, size, row, col, dir, word):
    result = puzzle_data[:]

    # Ensure the first and last letters do not abut another
    word_len = len(word)
    if dir == 'across':
        if ((col > 0 and result[row * size + col - 1] != BLANK) or
            (col < size - 1 and result[row * size + col + len(word)] != BLANK)):
            return None # Cannot abut on end or beginning
    else:
        if ((row > 0 and result[(row - 1) * size + col] != BLANK) or
            (row < size - 1 and result[(row + len(word)) * size + col] != BLANK)):
            return None # Cannot abut on end or beginning

    for i, letter in enumerate(word):
        pd_index = row * size + col
        if dir == 'across':
            pd_index += i
        else:
            pd_index += i * size

        existing = result[pd_index]
        if existing == BLANK:
            # Look to the sides to ensure we aren't inadvertently creating an
            # adjacent word. This makes our crosswords sparse.
            if dir == 'across':
                if row > 0 and result[pd_index - size] != BLANK:
                    return None

                if row < size - 1 and result [pd_index + size] != BLANK:
                    return None
            else:
                if col > 0 and result[pd_index - 1] != BLANK:
                    return None

                if col < (size - 1) and result[pd_index + 1] != BLANK:
                    return None
        elif existing != letter:
            return None  # Conflict

        result[pd_index] = letter

    return result


def try_to_expand_word(puzzle_data, size, used_word_map, row, col, dir, word):
    if (all(used_word_map)):
        return puzzle_data

    grid, cluelocs = puzzle_data

    new_dir = 'across' if dir == 'down' else 'down'
    for letter_offset, letter in enumerate(word):
        cross_words = cross_lookup[letter]
        for word_index, word_offset in cross_words:
            if used_word_map[word_index]:
                continue

            new_word = clues[word_index][0]

            if new_dir == 'across':
                new_row = row + letter_offset
                new_col = col - word_offset
            else:
                new_row = row - word_offset
                new_col = col + letter_offset

            if new_col < 0 or new_row < 0:
                continue
            if new_dir == 'across' and new_col + len(new_word) >= size:
                continue
            if new_dir == 'down' and new_row + len(new_word) >= size:
                continue

            new_grid = try_to_add_word(grid, size, new_row, new_col,
                                       new_dir, new_word)
            if new_grid:
                new_clues = cluelocs[:]
                new_clues[word_index] = (new_row, new_col, new_dir)
                used_word_map[word_index] = True
                solution = try_to_expand_word((new_grid, new_clues), size,
                                              used_word_map, new_row,
                                              new_col, new_dir, new_word)
                if solution:
                    return solution

                used_word_map[word_index] = False

    return None

def create_puzzle(size):
    # Place initial word near the middle of the puzzle
    empty_grid = [BLANK for _ in range(size * size)]
    used_word_map = [False for _ in range(len(clues))]

    initial_word_index = 0  # XXX Should pick longest
    used_word_map[initial_word_index] = True
    initial_word = clues[initial_word_index][0]
    initial_word_row = size // 2
    initial_word_col = (size - len(initial_word)) // 2
    new_grid = try_to_add_word(empty_grid, size, initial_word_row,
                               initial_word_col, 'across',
                               initial_word)
    if new_grid == None:
        print('Internal error: cannot place initial word')
        return None

    clue_locs = [None for _ in range(len(clues))]
    clue_locs[0] = (initial_word_row, initial_word_col, 'across')
    return try_to_expand_word((new_grid, clue_locs), size, used_word_map, initial_word_row,
                       initial_word_col, 'across', initial_word)

def write_puzzle_json(size, grid, clue_locs):
    answers = []
    for row in range(size):
        answers.append(''.join(grid[row * size:(row + 1) * size]))

    # Number our clues. We'd like these generally to go left-to-right,
    # top-to-bottom. Using our number map also allows us to ensure across/down
    # clues that share a starting cell have the same number
    locs = [(row, col) for row, col, _ in clue_locs]
    locs.sort()
    number_map = {}
    next_index = 1
    for row, col in locs:
        if (row, col) not in number_map:
            number_map[(row, col)] = next_index
            next_index += 1

    out_clues = []
    for i in range(len(clues)):
        row, col, dir = clue_locs[i]
        _, hint = clues[i]
        out_clues.append({
            'row': row,
            'col': col,
            'hint': hint,
            'num': number_map[(row, col)],
            'dir': dir
        })

    result = {
        'title': 'insert title',
        'numRows': size,
        'numCols': size,
        'answers': answers,
        'clues': out_clues,
    }

    print(json.dumps(result, indent=4))

def pretty_print_puzzle(puzzle, size):
    for i, letter in enumerate(puzzle):
        print(letter, sep='', end='')
        if i % size == size - 1:
            print()

def load_clues(filename):
    global clues
    clues = []
    with open(filename, 'r') as cluefile:
        for line in cluefile:
            word, hint = line.split(' ', 1)
            clues.append((word, hint.strip()))

def main():
    load_clues(sys.argv[1])
    size = int(sys.argv[2])
    init_cross_lookup()
    result = create_puzzle(size)
    if result == None:
        print('cannot find a solution', file=sys.stderr)
    else:
        write_puzzle_json(size, *result)

if __name__ == '__main__':
    main()