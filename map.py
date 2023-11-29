"""
This module has been adapted from the BuTools project: https://github.com/ghorvath78/butools
"""
import numpy as np
import numpy.matlib as ml
import numpy.linalg as la
from numpy.random import rand

def CheckGenerator (Q, transient=False, prec=10e-14):
    """
    Checks if the matrix is a valid generator matrix: the 
    matrix is a square matrix, the matrix has positive or 
    zero off-diagonal elements, the diagonal of the matrix 
    is negative, the rowsum of the matrix is 0.
    
    If the "transient" parameter is set to false, it checks 
    if the real part of the maximum absolute eigenvalue is 
    less than zero and the rowsum is equal or less than 0. 
    
    Parameters
    ----------
    Q : matrix, shape (M,M)
        The generator to check.
    transient : bool, optional
        If true, the procedure checks if Q is a transient 
        generator, otherwise it checks if it is a valid 
        generator. The default value is false.
    prec : double, optional
        Entries with absolute value less than prec are 
        considered to be zeros. The default value is 1e-14.
        
    Returns
    -------
    r : bool
        The result of the check.
    """

    if not isinstance(Q,np.ndarray):
        Q = np.array(Q)
        
    if Q.shape[0]!=Q.shape[1]:
        return False

    if np.any(np.diag(Q)>=prec):
        return False

    N = Q.shape[0]
    odQ = Q<-prec
    for i in range(N):
        odQ[i,i] = 0

    if np.sum(np.any(odQ))>0:
        return False

    if transient:
        if np.max(np.sum(Q,1))>prec:
            return False

        if np.max(np.real(la.eigvals(Q)))>=prec:
            return False
    else:
        if np.any(np.abs(np.sum(Q,1))>prec):
            return False
    return True

def CheckMAPRepresentation (D0, D1, prec=10e-9):
    """
    Checks if the input matrixes define a continuous time MAP.
    
    Matrices D0 and D1 must have the same size, D0 must be a 
    transient generator matrix, D1 has only non-negative 
    elements, and the rowsum of D0+D1 is 0 (up to the numerical
    precision).
    
    Parameters
    ----------
    D0 : matrix, shape (M,M)
        The D0 matrix of the MAP to check
    D1 : matrix, shape (M,M)
        The D1 matrix of the MAP to check
    prec : double, optional
        Numerical precision, the default value is 1e-14
    
    Returns
    -------
    r : bool 
        The result of the check
    """

    if not CheckGenerator(D0,True):
        return False

    if D0.shape!=D1.shape:
        if butools.verbose:
            print ("CheckMAPRepresentation: D0 and D1 have different sizes!")
        return False

    if np.min(D1)<-prec:
        if butools.verbose:
            print ("CheckMAPRepresentation: D1 has negative element!")
        return False

    if np.any(np.abs(np.sum(D0+D1,1))>prec):
        if butools.verbose:
            print ("CheckMAPRepresentation: The rowsum of D0+D1 is not 0!")
        return False

    return True

def SamplesFromMAP (D0, D1, k, initial=None, prec=1e-14):
    """
    Generates random samples from a marked Markovian 
    arrival process.
    
    Parameters
    ----------
    D0,D1 : matrices of shape(M,M) of the MAP
    K : integer
        The number of samples to generate.
    initial: optional, initial state
    prec : double, optional
        Numerical precision to check if the input MMAP is
        valid. The default value is 1e-14.

    
    Returns
    -------
    x : matrix, shape(K,2)
        The random samples. Each row consists of two 
        columns: the inter-arrival time and the type of the
        arrival.        
    """
    D=(D0,D1)

    if not CheckMAPRepresentation (D0,D1):
        raise Exception("SamplesFromMMAP: Input is not a valid MMAP representation!")    

    N = D[0].shape[0]
    
    if initial==None:
        # draw initial state according to the stationary distribution
        stst = CTMCSolve(SumMatrixList(D)).A.flatten()
        cummInitial = np.cumsum(stst)
        r = rand()
        state = 0
        while cummInitial[state]<=r:
            state+=1
    else:
        state = initial

    # auxilary variables
    sojourn = -1.0/np.diag(D[0])
    nextpr = ml.matrix(np.diag(sojourn))*D[0]
    nextpr = nextpr - ml.matrix(np.diag(np.diag(nextpr)))
    for i in range(1,len(D)):
        nextpr = np.hstack((nextpr, np.diag(sojourn)*D[i]))
    nextpr = np.cumsum(nextpr,1)
    
    if len(D)>2:
        x = np.empty((k,2))
    else:
        x = np.empty(k)

    for n in range(k):
        time = 0

        # play state transitions
        while state<N :
            time -= np.log(rand()) * sojourn[state]
            r = rand()
            nstate = 0
            while nextpr[state,nstate]<=r:
                nstate += 1
            state = nstate
        if len(D)>2:
            x[n,0] = time
            x[n,1] = state//N
        else:
            x[n] = time
        state = state % N
    
    return x, state


#D0 = ml.matrix([[-0.17, 0, 0, 0.07],[0.01, -0.78, 0.03, 0.08],[0.22, 0.17, -1.1, 0.02],[0.04, 0.12, 0, -0.42]])
#D1 = ml.matrix([[0, 0.06, 0, 0.04],[0.04, 0.19, 0.21, 0.22],[0.22, 0.13, 0.15, 0.19],[0.05, 0, 0.17, 0.04]])
#iat, s = SamplesFromMAP((D0, D1), 1, initial=1)
