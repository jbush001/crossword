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
import argparse

BLACK_SQUARE = '_'
clues = []
letter_to_word_offs = {}


def init_lookup_table():
    """Create a lookup table to find all words that have a specific letter in
    them.
    """
    for word_index, (word, _) in enumerate(clues):
        for offset, letter in enumerate(word):
            if letter in letter_to_word_offs:
                letter_to_word_offs[letter].append((word_index, offset))
            else:
                letter_to_word_offs[letter] = [(word_index, offset)]


def try_to_add_word(puzzle_data, size, row, col, dir, word):
    """Insert a new word into the current working puzzle and return a
    new instance.

    Args:
        puzzle_data: array.
          Each entry in the array represents one cell in the puzzle.
        size: int
          Number of cells vertically and horizontally.
        row: int
          0 based index starting from top of the start of this word
        col: int
          0 based index starting from left of the start of this word
        dir: string
          Can be 'across' or 'down' describing the direction of the clue.
        word: string
          Contents of the word

    Returns:
        A newly allocated array, based on puzzle_data, with the new
        word inserted if it fits.
        None if the word will not fit for some reason
    """
    result = puzzle_data[:]

    # Ensure the first and last letters do not abut another
    if dir == 'across':
        if ((col > 0 and result[row * size + col - 1] != BLACK_SQUARE) or
            (col < size - 1 and result[row * size + col + len(word)] != BLACK_SQUARE)):
            return None # Cannot abut on end or beginning
    else:
        if ((row > 0 and result[(row - 1) * size + col] != BLACK_SQUARE) or
            (row < size - 1 and result[(row + len(word)) * size + col] != BLACK_SQUARE)):
            return None # Cannot abut on end or beginning

    for i, letter in enumerate(word):
        pd_index = row * size + col
        if dir == 'across':
            pd_index += i
        else:
            pd_index += i * size

        existing = result[pd_index]
        if existing == BLACK_SQUARE:
            # Look to the sides to ensure we aren't inadvertently creating an
            # adjacent word. This makes our crosswords sparse.
            if dir == 'across':
                if row > 0 and result[pd_index - size] != BLACK_SQUARE:
                    return None

                if row < size - 1 and result [pd_index + size] != BLACK_SQUARE:
                    return None
            else:
                if col > 0 and result[pd_index - 1] != BLACK_SQUARE:
                    return None

                if col < (size - 1) and result[pd_index + 1] != BLACK_SQUARE:
                    return None
        elif existing != letter:
            return None  # Conflict

        result[pd_index] = letter

    return result


def try_to_expand_word(puzzle_data, size, used_word_map, row, col, dir, word):
    """Attempts to find another word that will orthoganlly fit with this word.

    This uses a simplistic algorithm that doesn't do a great job fitting.
    It will sort of make a spiral of clues, as it only crosses each clue
    deliberately once.

    Args:
        puzzle_data: tuple (grid, clues)
            Initial puzzle state
        size: int
            Number of cells vertically and horizontally
        used_word_map: array bool
            One entry for each clue. True if it has already been placed,
            False if not. This is updated in-place.
        row: int
            Vertical index of the start of the word to try to cross
        col: int
            Same as above, except horizontal
        dir: string: 'across' | 'down'
            Which direction the word to cross is oriented
        word: string
            The word we are trying to cross.

    Returns:
        A tuple of the puzzle grid and a clue array that contains start
        positions for each placed clue on success.
        None if it was unable to fit any words.
    """
    if all(used_word_map):
        return puzzle_data

    grid, cluelocs = puzzle_data

    new_dir = 'across' if dir == 'down' else 'down'
    for letter_offset, letter in enumerate(word):
        cross_words = letter_to_word_offs[letter]
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
    empty_grid = [BLACK_SQUARE for _ in range(size * size)]
    used_word_map = [False for _ in range(len(clues))]

    initial_word_index = 0  # This will be longest
    used_word_map[initial_word_index] = True
    initial_word = clues[initial_word_index][0]
    initial_word_row = size // 2
    initial_word_col = (size - len(initial_word)) // 2
    new_grid = try_to_add_word(empty_grid, size, initial_word_row,
                               initial_word_col, 'across',
                               initial_word)
    if new_grid is None:
        print('Internal error: cannot place initial word')
        return None

    clue_locs = [None for _ in range(len(clues))]
    clue_locs[0] = (initial_word_row, initial_word_col, 'across')
    return try_to_expand_word((new_grid, clue_locs), size, used_word_map, initial_word_row,
                       initial_word_col, 'across', initial_word)


def write_puzzle_json(filename, size, grid, clue_locs):
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
    for i, (_, hint) in enumerate(clues):
        row, col, direction = clue_locs[i]
        out_clues.append({
            'row': row,
            'col': col,
            'hint': hint,
            'num': number_map[(row, col)],
            'dir': direction
        })

    result = {
        'title': 'insert title',
        'numRows': size,
        'numCols': size,
        'answers': answers,
        'clues': out_clues,
    }

    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=4)


def pretty_print_puzzle(puzzle, size):
    for i, letter in enumerate(puzzle):
        print(letter, sep='', end='')
        if i % size == size - 1:
            print()


def load_clues(filename):
    """Read clues file, populate global clues array

    Args:
        filename: string
            Path to file

    Returns:
        Nothing
    """
    global clues
    clues = []
    with open(filename, 'r', encoding='utf8') as cluefile:
        for line in cluefile:
            word, hint = line.split(' ', 1)
            clues.append((word.strip(), hint.strip()))

    # Sort longest to shortest.
    clues.sort(key=lambda x: len(x[0]), reverse=True)


def main():
    parser = argparse.ArgumentParser(description='Generate a crossword puzzle')
    parser.add_argument('-o', '--output',
                        help='Output file to write (JSON format)',
                        default='puzzle.json')
    parser.add_argument('clue_file', help='list of clues to read')
    parser.add_argument('size', type=int, help='number of rows/columns')
    args = parser.parse_args()

    load_clues(args.clue_file)
    size = args.size
    init_lookup_table()
    result = create_puzzle(size)
    if result is None:
        print('cannot find a solution', file=sys.stderr)
    else:
        write_puzzle_json(args.output, size, *result)

if __name__ == '__main__':
    main()
