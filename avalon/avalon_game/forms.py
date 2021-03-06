from django import forms

from .models import Game, Player

class NewGameForm(forms.Form):
    name = forms.CharField(label='Name', max_length=80)

class JoinGameForm(forms.Form):
    game = forms.CharField(label='Access code',
                           max_length=Game.ACCESS_CODE_LENGTH)
    player = forms.CharField(label='Name', max_length=80)

    def clean_game(self):
        data = self.cleaned_data['game']

        try:
            return Game.objects.get(access_code=data.lower())
        except Game.DoesNotExist:
            raise forms.ValidationError("Invalid access code.")

    def clean(self):
        cleaned_data = super(JoinGameForm, self).clean()

        game = cleaned_data.get("game")
        name = cleaned_data.get("player")

        if game is None or name is None:
            return

        try:
            player = Player.objects.get(game=game, name=name)
            if player.is_expired():
                player.change_secret_id();
                player.save()
                cleaned_data["player"] = player
            else:
                self.add_error('player', "Please choose a different name; there is already a player using that name.")
                self.add_error('player', "Please try again in a few seconds if you are trying to rejoin.")
        except Player.DoesNotExist:
            if game.game_phase == Game.GAME_PHASE_LOBBY:
                player = Player.objects.create(game=game, name=name)
                cleaned_data["player"] = player
            else:
                self.add_error('player', "That game has already started. If you want to rejoin, please enter your name exactly as you did before.")

class StartGameForm(forms.Form):
    display_history = forms.BooleanField(required=False, initial=True,
                                         label="show history table")
    merlin = forms.BooleanField(required=False, initial=True, label="Merlin")
    percival = forms.BooleanField(required=False, initial=True,
                                  label="Percival")
    assassin = forms.BooleanField(required=False, initial=True,
                                  label="Assassin")
    morgana = forms.BooleanField(required=False, initial=True, label="Morgana")
    mordred = forms.BooleanField(required=False, initial=False,
                                 label="Mordred")
    oberon = forms.BooleanField(required=False, initial=False, label="Oberon")

    def clean(self):
        cleaned_data = super(StartGameForm, self).clean()

        merlin = cleaned_data.get("merlin")
        percival = cleaned_data.get("percival")
        assassin = cleaned_data.get("assassin")
        morgana = cleaned_data.get("morgana")
        mordred = cleaned_data.get("mordred")

        if assassin and not merlin:
            self.add_error('assassin', "The assassin requires Merlin to be in the game.")
        if percival and not merlin:
            self.add_error('percival', "Percival requires Merlin to be in the game.")
        if morgana and (not merlin or not percival):
            self.add_error('morgana', "Morgana requies Merlin and Percival to be in the game.")
        if mordred and not merlin:
            self.add_error('mordred', "Mordred requires Merlin to be in the game.")
