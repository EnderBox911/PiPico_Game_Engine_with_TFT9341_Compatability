import gc
import random
from Engine.game_base import GameBase


def mp_shuffle(lst):
    for i in range(len(lst) - 1, 0, -1):
        j = random.getrandbits(16) % (i + 1)
        lst[i], lst[j] = lst[j], lst[i]


class BlackjackGame(GameBase):
    """
    Blackjack UI + basic game logic.

    - Uses /bin_files/<Suit>_<Rank>.bin for card faces.
    - Uses /bin_files/Back_1.bin for the back of the dealer card.
    - Left button  = HIT
    - Right button = STAND
    """

    # Card sprite dimensions in pixels
    CARD_W = 37
    CARD_H = 52

    # Paths
    CARD_PATH_ROOT = "/bin_files/"
    CARD_BACK_FILE = "Back_{num}.bin"

    def __init__(self, engine):
        super().__init__(engine)

        self.gfx = engine.gfx
        self.width = self.gfx.width
        self.height = self.gfx.height

        # --- Colours (RGB565) ---
        self.OUTER_BG = 0x0000  # black border outside table
        self.TABLE_BORDER = 0xA145  # dark brown
        self.TABLE_GREEN = 0x03A0  # main felt
        self.TABLE_GREEN_DARK = 0x0200  # darker green for checker
        self.TEXT_WHITE = 0xFFFF
        self.TEXT_YELLOW = 0xFFE0

        # card area colours (velvet red)
        self.CARD_AREA_RED = 0x8800  # main red felt
        self.CARD_AREA_DARK_RED = 0x6000  # inner darker border

        # table layout
        self.margin = 8
        self.table_x = self.margin
        self.table_y = self.margin
        self.table_w = self.width - 2 * self.margin
        self.table_h = self.height - 2 * self.margin

        # vertical zones
        self.top_bar_h = 24
        self.bottom_bar_h = 32

        # button bar Y
        self.button_bar_y = self.table_y + self.table_h - self.bottom_bar_h

        # --- CENTRAL VELVET TABLE AREA ---
        self.card_area_x = self.table_x + 20
        self.card_area_w = self.table_w - 40
        self.card_area_y = self.table_y + 18
        self.card_area_h = self.button_bar_y - self.card_area_y - 6

        # card rows Y positions (inside velvet area)
        self.dealer_row_y = self.card_area_y + 42
        self.player_row_y = self.card_area_y + self.card_area_h - self.CARD_H - 10

        # center message Y (inside velvet area)
        self.message_y = self.card_area_y + self.card_area_h // 2 - 4

        # button sizes
        self.button_w = (self.table_w - 3 * 10) // 2  # 10px gaps
        self.button_h = 18

        # positions for buttons (inside table)
        self.hit_btn_x = self.table_x + 10
        self.stand_btn_x = self.table_x + 20 + self.button_w
        self.btn_y = self.button_bar_y + (self.bottom_bar_h - self.button_h) // 2

        # sprites cache: id -> sprite dict
        self.card_sprites = {}

        # draw static table once
        self._static_drawn = False

        # set up first round
        self._reset_round()

    def _reset_round(self):
        """Set up a fresh deck + hands."""
        self.state = "player_turn"
        self.dealer_timer = 0.0
        self.player_final = 0

        # back sprite random change
        self.dealer_back_sprite = self._load_card_sprite(self.CARD_BACK_FILE.format(num=random.randint(1, 5)))

        # full new deck
        self.deck = self._build_deck()
        mp_shuffle(self.deck)

        # deal initial cards
        self.player_cards = [self._draw_card_id()]
        self.dealer_cards = [self._draw_card_id()]

        self.status_text = "Blackjack demo"
        self.request_redraw()

    def reset(self):
        """
        Called by engine when user double-taps UP.
        Starts a completely new round.
        Clears caches.
        """
        self.card_sprites = {}

        self.gfx.clear_caches()
        gc.collect()

        self._reset_round()

    # ---------------------------------------------------------------------
    # Deck / card helpers
    # ---------------------------------------------------------------------

    def _build_deck(self):
        suits = ["Clubs", "Diamonds", "Hearts", "Spades"]
        ranks = ["2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "ACE"]
        deck = []
        for s in suits:
            for r in ranks:
                deck.append(f"{s}_{r}")
        return deck

    def _draw_card_id(self):
        if not self.deck:
            self.deck = self._build_deck()
            mp_shuffle(self.deck)
        return self.deck.pop()

    def _load_card_sprite(self, file_name):
        """Load a card sprite by its filename (e.g. 'Hearts_10.bin')."""
        full_path = self.CARD_PATH_ROOT + file_name
        return self.gfx.load_sprite_rgb565(full_path, self.CARD_W, self.CARD_H)

    def _get_card_sprite_for_id(self, card_id):
        """
        card_id example: 'Hearts_10' -> uses 'Hearts_10.bin'
        """
        if card_id not in self.card_sprites:
            file_name = card_id + ".bin"
            self.card_sprites[card_id] = self._load_card_sprite(file_name)
        return self.card_sprites[card_id]

    def _hand_value(self, card_ids):
        """
        Basic Blackjack hand value calculation.
        card_ids: list of 'Suit_RANK' strings.
        """
        total = 0
        aces = 0
        for cid in card_ids:
            rank = cid.split("_", 1)[1]
            if rank == "ACE":
                val = 11
                aces += 1
            elif rank in ("J", "Q", "K"):
                val = 10
            else:
                val = int(rank)
            total += val

        while total > 21 and aces > 0:
            total -= 10
            aces -= 1

        return total

    def _deal_initial_cards(self):
        self.player_cards = [self._draw_card_id()]
        self.dealer_cards = [self._draw_card_id()]
        self.state = "player_turn"
        self.status_text = "Blackjack demo"
        self.request_redraw()

    # ---------------------------------------------------------------------
    # Engine callbacks (buttons)
    # ---------------------------------------------------------------------

    def on_left_pressed(self):
        """Left button = HIT."""
        if self.state != "player_turn":
            return
        self._player_hit()

    def on_right_pressed(self):
        """Right button = STAND."""
        if self.state != "player_turn":
            return
        self._player_stand()

    def _player_hit(self):
        self.player_cards.append(self._draw_card_id())
        player_val = self._hand_value(self.player_cards)

        if player_val > 21:
            self.status_text = "Bust! You lose."
            self.state = "round_over"
        else:
            self.status_text = "You hit!"

        self.request_redraw()

    def _player_stand(self):
        # Player is done; dealer will auto-play with delay.
        self.player_final = self._hand_value(self.player_cards)
        self.status_text = "Dealer's turn..."
        self.state = "dealer_turn"
        self.dealer_timer = 0.0
        self.request_redraw()

    # ---------------------------------------------------------------------
    # GameBase hooks
    # ---------------------------------------------------------------------

    def update(self, dt, input_state):
        # Handle delayed dealer auto-play
        if self.state == "dealer_turn":
            self.dealer_timer += dt
            if self.dealer_timer >= 2.0:
                self.dealer_timer -= 2.0
                self._dealer_step()

    def _dealer_step(self):
        dealer_val = self._hand_value(self.dealer_cards)

        # If dealer already beat player, end immediately
        if self.player_final < dealer_val <= 21:
            self.status_text = "Dealer wins!"
            self.state = "round_over"
            self.request_redraw()
            return
        elif dealer_val == self.player_final and dealer_val == 21:
            self.status_text = "Draw!"
            self.state = "round_over"
            self.request_redraw()
            return

        # Otherwise take a card
        self.dealer_cards.append(self._draw_card_id())
        dealer_val = self._hand_value(self.dealer_cards)

        if dealer_val > 21:
            self.status_text = "Dealer busts! You win!"
            self.state = "round_over"
        elif dealer_val > self.player_final:
            self.status_text = "Dealer wins!"
            self.state = "round_over"
        else:
            self.status_text = "Dealer hits..."

        self.request_redraw()

    def draw(self, gfx):
        """
        Redraw only what’s needed.

        - Static table (border, felt, checker, labels, buttons) is drawn once.
        - For each change we redraw small regions: points, cards, status text.
        """
        if not self._static_drawn:
            self._draw_static_table(gfx)
            self._static_drawn = True

        # dynamic parts
        self._draw_points_only(gfx)
        self._draw_cards_only(gfx)
        self._draw_buttons_and_status(gfx)

        self.needs_redraw = False

    # ---------------------------------------------------------------------
    # Static drawing: table + labels + buttons (once)
    # ---------------------------------------------------------------------

    def _draw_static_table(self, gfx):
        # outer background
        gfx.clear(self.OUTER_BG)

        # overall table border (brown)
        gfx.fill_rect(self.table_x - 2, self.table_y - 2,
                      self.table_w + 4, self.table_h + 4, self.TABLE_BORDER)

        # whole table inner (green)
        gfx.fill_rect(self.table_x, self.table_y,
                      self.table_w, self.table_h, self.TABLE_GREEN)

        # checker pattern on the green felt (outside velvet)
        self._draw_checker_pattern(gfx)

        # --- CENTRAL VELVET TABLE ---
        # outer dark brown ring
        gfx.fill_rect(
            self.card_area_x - 4, self.card_area_y - 4,
            self.card_area_w + 8, self.card_area_h + 8,
            self.TABLE_BORDER,
        )
        # darker red border
        gfx.fill_rect(
            self.card_area_x - 2, self.card_area_y - 2,
            self.card_area_w + 4, self.card_area_h + 4,
            self.CARD_AREA_DARK_RED,
        )
        # inner red felt
        gfx.fill_rect(
            self.card_area_x, self.card_area_y,
            self.card_area_w, self.card_area_h,
            self.CARD_AREA_RED,
        )

        # --- static labels INSIDE velvet area ---
        label_x = self.card_area_x + 6
        dealer_label_y = self.card_area_y + 4
        player_label_y = self.player_row_y - 23

        gfx.draw_text(label_x, dealer_label_y, "Dealer", self.TEXT_WHITE,
                      bg=self.CARD_AREA_RED, scale=1)
        gfx.draw_text(label_x, dealer_label_y + 10, "Points:", self.TEXT_WHITE,
                      bg=self.CARD_AREA_RED, scale=1)

        gfx.draw_text(label_x, player_label_y, "Player", self.TEXT_WHITE,
                      bg=self.CARD_AREA_RED, scale=1)
        gfx.draw_text(label_x, player_label_y + 10, "Points:", self.TEXT_WHITE,
                      bg=self.CARD_AREA_RED, scale=1)

        # draw buttons (background + labels), static shape on the green bar
        self._draw_buttons_static(gfx)

    def _draw_checker_pattern(self, gfx):
        block = 8
        for y in range(self.table_y, self.table_y + self.table_h, block):
            for x in range(self.table_x, self.table_x + self.table_w, block):
                if ((x - self.table_x) // block + (y - self.table_y) // block) % 2 == 0:
                    gfx.fill_rect(x, y, block, block, self.TABLE_GREEN_DARK)

    # ---------------------------------------------------------------------
    # Dynamic drawing: numbers, cards, status, button highlight
    # ---------------------------------------------------------------------

    def _draw_points_only(self, gfx):
        # erase numeric parts and redraw them, on red velvet
        label_x = self.card_area_x + 6
        dealer_label_y = self.card_area_y + 4
        player_label_y = self.player_row_y - 23

        # dealer points area
        gfx.safe_fill_rect(label_x + 60, dealer_label_y + 10, 40, 10, self.CARD_AREA_RED)
        dealer_points = self._hand_value(self.dealer_cards)
        gfx.draw_text(label_x + 60, dealer_label_y + 10,
                      str(dealer_points), self.TEXT_YELLOW,
                      bg=self.CARD_AREA_RED, scale=1)

        # player points area
        gfx.safe_fill_rect(label_x + 60, player_label_y + 10, 40, 10, self.CARD_AREA_RED)
        player_points = self._hand_value(self.player_cards)
        gfx.draw_text(label_x + 60, player_label_y + 10,
                      str(player_points), self.TEXT_YELLOW,
                      bg=self.CARD_AREA_RED, scale=1)

    def _compute_card_positions(self, num_cards, row_y):
        if num_cards <= 0:
            return []

        area_x = self.card_area_x
        area_w = self.card_area_w

        spacing = self.CARD_W + 6
        total_width = spacing * (num_cards - 1) + self.CARD_W

        if total_width > area_w:
            spacing = max(2, (area_w - self.CARD_W) // max(1, (num_cards - 1)))
            total_width = spacing * (num_cards - 1) + self.CARD_W

        start_x = area_x + (area_w - total_width) // 2
        xs = [start_x + i * spacing for i in range(num_cards)]
        ys = [row_y] * num_cards
        return list(zip(xs, ys))

    def _draw_cards_only(self, gfx):
        # Clear dealer + player card rows to red felt, then redraw cards.

        row_height = self.CARD_H + 4

        # dealer row (inside card area)
        gfx.safe_fill_rect(
            self.card_area_x,
            self.dealer_row_y,
            self.card_area_w,
            row_height,
            self.CARD_AREA_RED,
        )

        # player row (inside card area)
        gfx.safe_fill_rect(
            self.card_area_x,
            self.player_row_y,
            self.card_area_w,
            row_height,
            self.CARD_AREA_RED,
        )

        # Dealer: back + one or more front cards
        dealer_positions = self._compute_card_positions(
            max(2, len(self.dealer_cards) + 1),
            self.dealer_row_y,
        )

        if len(dealer_positions) >= 2:
            (back_x, back_y), first_front = dealer_positions[0], dealer_positions[1]
        else:
            back_x = self.table_x + (self.table_w - self.CARD_W) // 2
            back_y = self.dealer_row_y
            first_front = (back_x + self.CARD_W + 4, back_y)

        # back card
        gfx.draw_sprite(self.dealer_back_sprite, back_x, back_y)

        # front dealer cards
        for idx, cid in enumerate(self.dealer_cards):
            if idx == 0:
                fx, fy = first_front
            else:
                # subsequent cards follow positions after the first front
                pos_index = min(idx + 1, len(dealer_positions) - 1)
                fx, fy = dealer_positions[pos_index]
            sprite = self._get_card_sprite_for_id(cid)
            gfx.draw_sprite(sprite, fx, fy)

        # Player cards row
        player_positions = self._compute_card_positions(
            len(self.player_cards), self.player_row_y
        )
        for card_id, (cx, cy) in zip(self.player_cards, player_positions):
            sprite = self._get_card_sprite_for_id(card_id)
            gfx.draw_sprite(sprite, cx, cy)

    def _draw_buttons_static(self, gfx):
        # Buttons are rectangles with text "HIT" and "STAND"
        btn_col = 0x632C
        outline = 0xFFFF

        # Hit button shape
        gfx.fill_rect(self.hit_btn_x, self.btn_y, self.button_w, self.button_h, btn_col)
        gfx.safe_fill_rect(self.hit_btn_x, self.btn_y, self.button_w, 1, outline)
        gfx.safe_fill_rect(self.hit_btn_x, self.btn_y + self.button_h - 1,
                           self.button_w, 1, outline)
        gfx.safe_fill_rect(self.hit_btn_x, self.btn_y, 1, self.button_h, outline)
        gfx.safe_fill_rect(self.hit_btn_x + self.button_w - 1, self.btn_y,
                           1, self.button_h, outline)

        # Stand button shape
        gfx.fill_rect(self.stand_btn_x, self.btn_y, self.button_w, self.button_h, btn_col)
        gfx.safe_fill_rect(self.stand_btn_x, self.btn_y, self.button_w, 1, outline)
        gfx.safe_fill_rect(self.stand_btn_x, self.btn_y + self.button_h - 1,
                           self.button_w, 1, outline)
        gfx.safe_fill_rect(self.stand_btn_x, self.btn_y, 1, self.button_h, outline)
        gfx.safe_fill_rect(self.stand_btn_x + self.button_w - 1, self.btn_y,
                           1, self.button_h, outline)

        # Static button labels
        hit_label = "HIT"
        stand_label = "STAND"
        hit_w, hit_h = self.gfx.get_text_size(hit_label, scale=1)
        stand_w, stand_h = self.gfx.get_text_size(stand_label, scale=1)

        hit_tx = self.hit_btn_x + (self.button_w - hit_w) // 2
        hit_ty = self.btn_y + (self.button_h - hit_h) // 2
        gfx.draw_text(hit_tx, hit_ty, hit_label, self.TEXT_WHITE,
                      bg=btn_col, scale=1)

        stand_tx = self.stand_btn_x + (self.button_w - stand_w) // 2
        stand_ty = self.btn_y + (self.button_h - stand_h) // 2
        gfx.draw_text(stand_tx, stand_ty, stand_label, self.TEXT_WHITE,
                      bg=btn_col, scale=1)

    def _draw_buttons_and_status(self, gfx):
        """
        Only redraw status text (buttons are static).
        """
        msg = self.status_text
        msg_w, msg_h = self.gfx.get_text_size(msg, scale=1)
        msg_x = self.card_area_x + (self.card_area_w - msg_w) // 2
        msg_y = self.message_y

        # clear behind message inside velvet area
        gfx.safe_fill_rect(self.card_area_x,
                           msg_y,
                           self.card_area_w,
                           msg_h,
                           self.CARD_AREA_RED)

        gfx.draw_text(msg_x, msg_y, msg, self.TEXT_WHITE,
                      bg=self.CARD_AREA_RED, scale=1)

