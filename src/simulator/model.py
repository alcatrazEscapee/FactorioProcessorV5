from typing import List, Set
from networkx import Graph
from networkx.algorithms.components import connected_components
from simulator import Signal, Entity


class Model:
    """ The model of a collection of entities. Handles updating them in Factorio style ticks and provides builders for their network connections """

    def __init__(self):
        self.network: Graph = Graph()
        self.network_connections: List[Set[Signal]] = []
        self.entities: List[Entity] = []

        self.is_initialized = True
        self.tick_count = 0

    def add_entity(self, ent: Entity):
        self.entities.append(ent)
        self.is_initialized = False

    def get_entity(self, entity_id: int) -> Entity:
        return self.entities[entity_id - 1]

    def add_connection(self, left: Signal, right: Signal):
        self.network.add_edge(left, right)
        self.is_initialized = False

    def tick(self, times: int = 1):
        if not self.is_initialized:
            # Sets up network connections
            self.network_connections = [p for p in connected_components(self.network)]
            self.is_initialized = True

        for _ in range(times):
            # Update all network connections
            for group in self.network_connections:
                # Set each network node to the sum of all signals in the group
                signal_sum = Signal()
                for s in group:
                    signal_sum += s  # the values this node is sending

                for s in group:
                    s.update(signal_sum)

            # Tick all entities
            for ent in self.entities:
                ent.tick()

            self.tick_count += 1  # Increment tick counter

    def __str__(self):
        return 'EntityModel:\n :%s' % '\n :'.join(str(e) for e in self.entities)
