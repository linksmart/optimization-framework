#from . import core

#core.hmm()

import requests
from . import core

def main():
    response=requests.get('https://httpbin.org/ip')

    print('Your IP is {0}'.format(response.json()['origin']))

if __name__ == "__main__":
    main()