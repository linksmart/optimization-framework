import threading
import time
from abc import ABC, abstractmethod
from multiprocessing import Process

class rec(ABC):

    def __init__(self, a):
        self.a = a
        self.b = False
        self.data = "a"
        #threading.Thread(target=self.l).start()

    def get_data(self):
        print(self.a,self.b)
        ctr = 0
        print("rec" + str(self.data) + " " + str(self.b))
        while not self.b:
            print("rec" + str(self.data) + " " + str(self.b))
            time.sleep(2)
            ctr += 1
            if ctr > 5:
                break
        return self.data

    @abstractmethod
    def data_rec(self, data):
        pass

class baserec(rec, ABC):

    def __init__(self, a):
        super(baserec, self).__init__(a)
        self.c = 3

    def data_rec(self, data):
        self.data = data
        self.b = True

    def get_data_final(self):
        print(self.c,self.b, self.data)
        return self.get_data()

class gen(baserec):

    def __init__(self, a):
        super(gen, self).__init__(a)

class inpu:

    def __init__(self):
        self.e = 4
        self.g = gen(6)

    def gd(self):
        return self.g.get_data_final()

    def sd(self, data):
        self.g.data_rec(data)

class mybase(ABC):

    def __init__(self, b, c, q):
        super(mybase, self).__init__()
        print("my base")
        self.b = b
        self.c = c
        self.q = q
        self.ipc = inpu()

    @abstractmethod
    def ads(self):
        pass

    def p(self):
        print(self.b,self.c)


class mythreadclass(mybase, threading.Thread, ABC):

    def __init__(self, a, b, c):
        super(mythreadclass, self).__init__(b, c)
        self.a = a
        print("my thread init")

    def run(self):
        while True:
            print("my thread run " + self.a)
            self.p()
            self.ads()
            print(self.ipc.gd())
            time.sleep(10)
            self.ipc.sd("it works")

class myprocessclass(mybase, Process, ABC):

    def __init__(self, a, b, c, q):
        super(myprocessclass, self).__init__(b, c, q)
        self.a = a
        print("my procss init")

    def run(self):
        while True:
            print("my process run " + self.a)
            self.p()
            self.ads()
            print(self.pid)
            print(self.q.p())
            print(self.ipc.gd())
            time.sleep(10)
            self.ipc.sd("it works")

class ficlass(myprocessclass):

    def __init__(self, a, b, c, q):
        super().__init__(a, b, c, q)

    def ads(self):
        print("in ads")

class qwert:

    def __init__(self):
        self.y = 10
        self.z = 11

    def p(self):
        print(self.y*self.z)

if __name__ == '__main__':

    q = qwert()

    f = ficlass("a", "b", "c", q)
    f.start()