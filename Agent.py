import random
from agregate import Agregate
from agregate import AgType
import time
from copy import deepcopy

AGG = "flex"
MAX_CAP = "max_cap"
MIN_CAP = "min_cap"
NOTE_MAX = "note_max"
F = "f"
C = "c"
T = "t"
HIST_SIZE = 10


class Agent:
    lastId = 0
    agentList = []
    t_wait = 1

    def __init__(self, base_flex):
        self.id = Agent.lastId
        self.flex = base_flex  # random.randrange(100)
        self.x_max = self.flex
        self.x = self.x_max
        self.old_x = self.x
        self.note = random.randrange(10)
        self.infos = dict()
        self.infos[AGG] = Agregate(AgType.SUM, self.x, 1 if self.id == 0 else 0)
        self.infos[MAX_CAP] = Agregate(AgType.MAX, self.x, 0)
        self.infos[MIN_CAP] = Agregate(AgType.MIN, self.x, 0)
        self.infos[NOTE_MAX] = Agregate(AgType.MAX, self.note, 0)
        self.inbox = {}
        for k, v in self.infos.items():
            self.inbox[k] = [deepcopy(v)]  # envoi à soi-même des valeurs
        self.order = None
        self.cnt = self.cnt2 = self.mode = self.obj = 0
        self.stats = []
        self.base_conso = base_flex
        self.conso = self.base_conso
        self.m_cap = self.x
        self.eval = {F: 0, C: 0, T: 0}
        self.coefs = {F: 0.5, C: 0.4, T: 0.1}
        self.hist = {F: [], C: [], T: []}
        self.connect = 10
        Agent.agentList.append(self)
        Agent.lastId += 1

    def run(self):
        if self.order is not None and abs((self.infos[AGG].result() / self.order.Q) - 1) >= 0.0:  # if crossed
            if time.time() - self.cnt >= Agent.t_wait:  # filtre passe-bas
                # print(self.order.Q, " ", self.infos[AGG].result())
                self.x += (self.order.Q - self.infos[AGG].result()) * self.x / self.infos[AGG].result()  # MAJ
                self.cnt = time.time()
        else:
            self.cnt = time.time()
        if self.x >= self.x_max:
            self.x_max += (self.flex - self.x_max) * 0.5
        self.x_max = min(self.x_max, self.flex)
        self.x = min(self.x, self.x_max)
        if self.mode == 1:
            if self.order.td <= time.time():
                self.obj = self.x
                self.stats = [self.x]
                self.mode = 2
        if self.mode == 2:
            self.stats.append(self.x)
            self.conso = self.base_conso - self.x
            if self.order.tf < time.time():
                self.order = None
                self.evaluate()
                self.mode = 3
                self.conso = self.base_conso
                self.cnt2 = time.time()
        if self.mode == 3:
            if time.time() - self.cnt2 >= Agent.t_wait:
                if self.infos[MAX_CAP].result() - self.infos[MIN_CAP].result() != 0:
                    self.eval[C] = (self.m_cap - self.infos[MIN_CAP].result()) * HIST_SIZE / (
                        self.infos[MAX_CAP].result() - self.infos[MIN_CAP].result())
                    self.note = self.coefs[F] * self.eval[F] + self.coefs[C] * self.eval[C] + self.coefs[T] * self.eval[
                        T]
                self.infos[NOTE_MAX].update([self.note])
                self.mode = 0
            else:
                self.cnt2 = time.time()
        self.push_sum()

    def push_sum(self):
        for k, v in self.infos.items():
            v.update(self.inbox[k])
            if k == AGG:
                v.val += self.x - self.old_x
                self.old_x = self.x
            self.propagate(k, v)

    def propagate(self, k, v):
        message = v.message(k, self.connect)
        send(message, self.connect)
        self.receive(message)

    def receive(self, m):
        self.inbox[m.f].append(deepcopy(m.a))

    def evaluate(self):
        c = sum(self.stats) / float(len(self.stats))
        f = (1 if self.m_cap / self.obj >= 0.5 else 0) if self.obj > 0 else 1
        t = (1 if self.x_max / self.flex > 0.9 else 0) if self.flex > 0 else 1
        self.hist[F].append(f)
        self.hist[C].append(c)
        self.hist[T].append(t)
        self.eval[F] += f - self.hist[F].pop(0) if len(self.hist[F]) > HIST_SIZE else 0
        self.eval[T] += t - self.hist[T].pop(0) if len(self.hist[T]) > HIST_SIZE else 0
        if len(self.hist[C]) > HIST_SIZE:
            self.hist[C].pop(0)
        self.m_cap = sum(self.hist[C]) / float(len(self.hist[C]))
        self.propagate(MIN_CAP, Agregate(AgType.MIN, self.m_cap))
        self.propagate(MAX_CAP, Agregate(AgType.MAX, self.m_cap))

    def receive_order(self, o):
        if self.order is None or self.order.t < o.t:
            self.order = o
            send_order(o, self.connect)
            self.x_max = self.note * self.flex / self.infos[NOTE_MAX].result()
            self.x = self.x_max
            self.mode = 1


def send(m, j=1):
    for a in random.sample(Agent.agentList, j):
        a.receive(m)


def send_order(m, j=1):
    for a in random.sample(Agent.agentList, j):
        a.receive_order(m)
