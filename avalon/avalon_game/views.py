import math
import random

from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_safe,\
                                         require_POST,\
                                         require_http_methods

from .forms import NewGameForm, JoinGameForm, StartGameForm
from .helpers import mission_size, mission_size_string
from .models import Game, GameRound, Player

# helpers to interpret arguments
def lookup_access_code(func):
    def with_game(request, access_code, *args, **kwargs):
        game = get_object_or_404(Game, access_code=access_code)
        return func(request, game, *args, **kwargs)

    return with_game

def lookup_player_secret(func):
    def with_player(request, game, player_secret, *args, **kwargs):
        player = get_object_or_404(Player, game=game, secret_id=player_secret)
        return func(request, game, player, *args, **kwargs)

    return with_player


# views

@require_safe
def index(request):
    return render(request, 'index.html')

@require_http_methods(["HEAD", "GET", "POST"])
def enter_code(request):
    if request.method == 'POST':
        form = JoinGameForm(request.POST)
        if form.is_valid():
            game = form.cleaned_data.get('game')
            player = form.cleaned_data.get('player')
            return redirect('game',
                            access_code=game.access_code,
                            player_secret=player.secret_id)
    else:
        form = JoinGameForm()

    return render(request, 'join_game.html', {'form': form})

@require_http_methods(["HEAD", "GET", "POST"])
def new_game(request):
    if request.method == 'POST':
        form = NewGameForm(request.POST)
        if form.is_valid():
            game = Game.objects.create()
            name = form.cleaned_data.get('name')
            player = Player.objects.create(game=game, name=name)
            return redirect('game',
                            access_code=game.access_code,
                            player_secret=player.secret_id)
    else:
        form = NewGameForm()

    return render(request, 'new_game.html', {'form': form})

@lookup_access_code
@require_safe
def join_game(request, game):
    form = JoinGameForm(initial={'game': game.access_code})
    return render(request, 'join_game.html', {'access_code': game.access_code,
                                              'form': form})

def game_base_context(game, player):
    players = Player.objects.filter(game=game).order_by('order')
    num_players = players.count()

    context = {}

    context['access_code'] = game.access_code
    context['player_secret'] = player.secret_id
    context['players'] = players
    context['player'] = player

    try:
        round_scores = {}
        for round_num in range(1, 6):
            round_scores[round_num] = {'mission_size': mission_size_string(mission_size(num_players=num_players, round_num=round_num)), 'winner': ''}
        for game_round in GameRound.objects.filter(game=game):
            round_scores[game_round.round_num]['winner'] = game_round.winner_string()
        context['round_scores'] = round_scores
    except ValueError:
        pass

    if game.game_phase != Game.GAME_PHASE_LOBBY:
        context['game_has_mordred'] = players.filter(role=Player.ROLE_MORDRED)\
                                             .exists()
        context['visible_spies'] = [p for p in players
                                    if player.sees_as_spy(p)]
        if player.is_percival():
            possible_merlins = " or ".join([p.name for p in players
                                            if p.appears_as_merlin()])
            context['possible_merlins'] = possible_merlins

    return context

@lookup_access_code
@lookup_player_secret
@require_safe
def game(request, game, player):
    player.save() # update last_accessed

    context = game_base_context(game, player)

    if game.game_phase == Game.GAME_PHASE_LOBBY:
        context['form'] = StartGameForm()
        return render(request, 'lobby.html', context)
    elif game.game_phase == Game.GAME_PHASE_ROLE:
        return render(request, 'role_phase.html', context)
    elif game.game_phase == Game.GAME_PHASE_PICK:
        pass
    elif game.game_phase == Game.GAME_PHASE_VOTE:
        pass
    elif game.game_phase == Game.GAME_PHASE_MISSION:
        pass
    elif game.game_phase == Game.GAME_PHASE_ASSASSIN:
        pass
    elif game.game_phase == Game.GAME_PHASE_END:
        pass
    else:
        pass

    return render(request, 'in_game.html', context)

@lookup_access_code
@lookup_player_secret
@require_POST
def leave(request, game, player):
    player.delete()
    num_players = Player.objects.filter(game=game).count()
    if num_players == 0:
        game.delete()
    return redirect('index')

@lookup_access_code
@lookup_player_secret
@require_POST
def start(request, game, player):
    player.save() # update last_accessed

    if game.game_phase != Game.GAME_PHASE_LOBBY:
        return redirect('game', access_code=game.access_code,
                        player_secret=player.secret_id)

    players = Player.objects.filter(game=game)
    num_players = players.count()

    form = StartGameForm(request.POST)
    if num_players < 5:
        form.add_error(None, "You must have at least 5 players to play!")
    elif num_players > 10:
        form.add_error(None, "You can't have more than 10 players to play!")

    if form.is_valid():
        num_spies = int(math.ceil(num_players / 3.0))
        spy_roles = []
        if form.cleaned_data.get('assassin'):
            spy_roles.append(Player.ROLE_ASSASSIN)
        if form.cleaned_data.get('morgana'):
            spy_roles.append(Player.ROLE_MORGANA)
        if form.cleaned_data.get('mordred'):
            spy_roles.append(Player.ROLE_MORDRED)
        if form.cleaned_data.get('oberon'):
            spy_roles.append(Player.ROLE_OBERON)
        if len(spy_roles) > num_spies:
            form.add_error(None, "There will only be %d spies. Select no more than that many special roles for spies." % num_spies)
        else:
            game.display_history = form.cleaned_data.get('display_history')
            game.game_phase = Game.GAME_PHASE_ROLE

            resistance_roles = []
            if form.cleaned_data.get('merlin'):
                resistance_roles.append(Player.ROLE_MERLIN)
            if form.cleaned_data.get('percival'):
                resistance_roles.append(Player.ROLE_PERCIVAL)

            num_resistance = num_players - num_spies
            roles = spy_roles + resistance_roles +\
                    [Player.ROLE_SPY]*(num_spies - len(spy_roles)) +\
                    [Player.ROLE_GOOD]*(num_resistance - len(resistance_roles))
            assert len(roles) == num_players

            play_order = range(num_players)
            random.shuffle(play_order)
            random.shuffle(roles)

            for p, role, order in zip(players, roles, play_order):
                p.role = role
                p.order = order
                p.save()

            game.save()
            return redirect('game', access_code=game.access_code,
                            player_secret=player.secret_id)
    context = game_base_context(game, player)
    context['form'] = form

    return render(request, 'lobby.html', context)

@lookup_access_code
@lookup_player_secret
@require_POST
def ready(request, game, player):
    if game.game_phase == Game.GAME_PHASE_ROLE:
        player.ready = True
        player.save()

        if not Player.objects.filter(game=game, ready=False):
            game.game_phase = Game.GAME_PHASE_PICK
            game.save()
            GameRound.objects.create(game=game, round_num=1)

    return redirect('game', access_code=game.access_code,
                    player_secret=player.secret_id)

@lookup_access_code
@lookup_player_secret
def choose(request, game, player, round_num, vote_num, who):
    pass

@lookup_access_code
@lookup_player_secret
def unchoose(request, game, player, round_num, vote_num, who):
    pass

@lookup_access_code
@lookup_player_secret
def vote(request, game, player, round_num, vote_num, vote):
    pass

@lookup_access_code
@lookup_player_secret
def mission(request, game, player, round_num, mission_action):
    pass

@lookup_access_code
@lookup_player_secret
def assassinate(request, game, player, target):
    pass
