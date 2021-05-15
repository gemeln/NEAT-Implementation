from .counter import Counter
from .node import Node
from .edge import Edge
import numpy as np
import numpy.random as random

EDGE_MUTATION_RATE = 0.05
ADD_EDGE_MUTATION_RATE = 0.02
ADD_NODE_MUTATION_RATE = 0.01
MUTATION_STRENGTH = 0.3
ADD_NODE_MUTATION_NUMBER = 5
ADD_EDGE_MUTATION_NUMBER = 5


def sigmoid(x):
    return 1/(1 + np.exp(-x))


def tanh(x):
    return np.tanh(x)


class Network():
    nodeInnv = Counter()
    edgeInnv = Counter()

    def __init__(self, numInputs, numOutputs, numRNN, activation=tanh, empty=False):
        # structure of nodes array: [i,hi,o,ho,hh]
        if not empty:
            self.nodes = [Node(Network.nodeInnv.post())
                          for i in range(numInputs+numOutputs+2*numRNN)]
        else:
            self.nodes = []
        self.edges = []
        self.numInputs = numInputs
        self.numOutputs = numOutputs
        self.numRNN = numRNN
        self.activation = activation

    # Helper to add Edge going between NodeIn and NodeOut, default weight to 1
    def _add_edge(self, nodeIn: 'Node', nodeOut: 'Node', weight=None, enable=True):
        if weight is None:
            weight = random.normal()
        newEdge = Edge(nodeIn, nodeOut,
                       Network.edgeInnv.post(), weight, enable)
        self.edges.append(newEdge)
        nodeOut.edgesIn.append(newEdge)
        return newEdge

    def _add_node(self):
        newNode = Node(Network.nodeInnv.post())
        self.nodes.append(newNode)
        return newNode

    # Pick two random nodes, add edge between them, edge cannot go to input node
    def mutate_add_edge(self):
        validConfig = False
        numNodes = len(self.nodes)
        numHidden = numNodes - (self.numInputs +
                                self.numOutputs+2*self.numRNN)
        while not validConfig:
            validConfig = True
            node1Num = (random.randint(self.numInputs+self.numRNN+numHidden) -
                        numHidden) % numNodes   # Pick from inputs or hidden
            # pick from outputs or hidden
            node2Num = random.randint(self.numInputs+self.numRNN, numNodes)
            if node1Num == node2Num:  # Same node
                validConfig = False
                continue
            # If node2 is output node, it will be the ending node
            if (node2Num >= self.numInputs + self.numRNN) and (node2Num < self.numInputs + self.numRNN * 2 + self.numOutputs):
                nodeFrom = self.nodes[node1Num]
                nodeTo = self.nodes[node2Num]
            # If node1 is an input node, it will be the starting node
            elif node2Num < self.numInputs:
                nodeFrom = self.nodes[node1Num]
                nodeTo = self.nodes[node2Num]
            else:
                nodeTo = self.nodes[node1Num]
                nodeFrom = self.nodes[node2Num]

            for edge in nodeTo.edgesIn:  # Edge already exists
                if edge.nodeIn == nodeFrom:
                    validConfig = False
                    break
        self._add_edge(nodeFrom, nodeTo)

    ''' Pick edge, insert node between NodeIn and NodeOut of edge,
    weight between new node and NodeOut is 1, weight between NodeIn and
    new node is weight of old edge'''

    def mutate_add_node(self):
        if(len(self.edges) == 0):
            self.mutate_add_edge()
            return
        validConfig = False
        while not validConfig:
            edgeNum = random.randint(0, len(self.edges))
            validConfig = self.edges[edgeNum].enable
        pickedEdge = self.edges[edgeNum]
        pickedEdge.enable = False
        newNode = self._add_node()
        self._add_edge(pickedEdge.nodeIn, newNode, weight=pickedEdge.weight)
        self._add_edge(newNode, pickedEdge.nodeOut, weight=1)

    # Return value inside node to pass through edge
    def _evalNode(self, node):
        if(node.visited):
            return node.val
        node.visited = True

        for edge in node.edgesIn:
            if edge.enable:
                node.val += edge.weight * self._evalNode(edge.nodeIn)

        node.val = self.activation(node.val)  # Activation
        return node.val

    # Run one prediction
    def feedforward(self, inputValues):
        assert(len(inputValues) == self.numInputs)
        for i in range(self.numInputs):  # Set input nodes to values of inputs
            self.nodes[i].val = inputValues[i]
            self.nodes[i].visited = True

        output = np.empty(self.numOutputs)
        for i in range(self.numOutputs):
            outputNode = self.nodes[self.numInputs+self.numRNN+i]
            print("Evaluating output "+str(outputNode))
            output[i] = self._evalNode(outputNode)

        # Hidden outputs
        for i in range(self.numRNN):
            outputNode = self.nodes[self.numInputs +
                                    self.numRNN+self.numOutputs+i]
            print("Evaluating hidden output "+str(outputNode))
            self._evalNode(outputNode)
        # Hidden inputs
        for i in range(self.numRNN):
            self.nodes[self.numInputs+i].visited = True
            self.nodes[self.numInputs+i].val = self.nodes[self.numInputs +
                                                          self.numRNN + self.numOutputs + i].val

        # Reset graph for next time step
        for nodeNum in range(self.numInputs + self.numRNN, len(self.nodes)):
            node = self.nodes[nodeNum]
            node.val = 0
            node.visited = False

        return output

    @staticmethod
    def crossover(net1: "Network", net2: "Network") -> "Network":
        newNet = Network(net1.numInputs, net1.numOutputs,
                         net1.numRNN, empty=True)

        # Add Nodes to new net
        added = {}
        for node in net1.nodes:
            newNode = node.copyConstructor()
            newNet.nodes.append(newNode)
            added[node.innv] = newNode

        for node in net2.nodes:
            if node.innv not in added:
                newNode = node.copyConstructor()
                newNet.nodes.append(newNode)
                added[node.innv] = newNode

        # Add Edges to new net
        edgeNum1 = 0
        edgeNum2 = 0
        while edgeNum1 < len(net1.edges) or edgeNum2 < len(net2.edges):
            if edgeNum1 == len(net1.edges):
                # Helper copy net2[edge2Num]
                newEdge = net2.edges[edgeNum2].copyEdge(added)
                edgeNum2 += 1
            elif edgeNum2 == len(net2.edges):
                # Helper copy net1[edge1Num]
                newEdge = net1.edges[edgeNum1].copyEdge(added)
                edgeNum1 += 1
            else:
                if net1.edges[edgeNum1].innv < net2.edges[edgeNum2].innv:
                    newEdge = net1.edges[edgeNum1].copyEdge(added)
                    edgeNum1 += 1
                elif net1.edges[edgeNum1].innv > net2.edges[edgeNum2].innv:
                    newEdge = net2.edges[edgeNum2].copyEdge(added)
                    edgeNum2 += 1
                else:
                    newEdge = net2.edges[edgeNum2].copyEdge(added)
                    edgeNum1 += 1
                    edgeNum2 += 1

            if random.random() < EDGE_MUTATION_RATE:
                newEdge.weight = newEdge.weight + \
                    (random.normal() * MUTATION_STRENGTH)

            newNet.edges.append(newEdge)

        # Pick number of new nodes to muate using a binomial distribution
        for i in range(random.binomial(ADD_NODE_MUTATION_NUMBER, ADD_NODE_MUTATION_RATE)):
            newNet.mutate_add_node()
        # Pick number of new edges to muate using a binomial distribution
        for i in range(random.binomial(ADD_EDGE_MUTATION_NUMBER, ADD_EDGE_MUTATION_RATE)):
            newNet.mutate_add_edge()

        return newNet
