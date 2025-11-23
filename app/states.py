from aiogram.fsm.state import State, StatesGroup


class BuyEnergyStates(StatesGroup):
    waiting_for_address = State()


class ProvideEnergyStates(StatesGroup):
    waiting_for_address = State()
