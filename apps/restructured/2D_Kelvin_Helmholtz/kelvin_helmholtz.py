#!/usr/bin/env python
from opensbli import *
import numpy as np
from opensbli.core.weno_opensbli import RoeAverage, LLFWeno
from opensbli.utilities.helperfunctions import output_hdf5

ndim = 2
# Specify TENO order and initialise characteristic scheme.
sc1 = "**{\'scheme\':\'Weno\'}"
# Define the compresible Navier-Stokes equations in Einstein notation.
mass = "Eq(Der(rho,t), - Conservative(rhou_j,x_j,%s))" % sc1
momentum = "Eq(Der(rhou_i,t) , -Conservative(rhou_i*u_j + KD(_i,_j)*p,x_j , %s)  )" % sc1
energy = "Eq(Der(rhoE,t), - Conservative((p+rhoE)*u_j,x_j, %s))" % sc1
# Substitutions
substitutions = []
constants = ["gama", "Minf"]
# Define coordinate direction symbol (x) this will be x_i, x_j, x_k
coordinate_symbol = "x"
# Formulas for the variables used in the equations
velocity = "Eq(u_i, rhou_i/rho)"
pressure = "Eq(p, (gama-1)*(rhoE - rho*(1/2)*(KD(_i,_j)*u_i*u_j)))"
speed_of_sound = "Eq(a, (gama*p/rho)**0.5)"

# Instatiate equation classes
eq = EinsteinEquation()
base_eqns = [mass, momentum, energy]
constituent_eqns = [velocity, pressure, speed_of_sound]

simulation_eq = SimulationEquations()
constituent = ConstituentRelations()

for eqn in base_eqns:
    simulation_eq.add_equations(eq.expand(eqn, ndim, coordinate_symbol, substitutions, constants))

for eqn in constituent_eqns:
    constituent.add_equations(eq.expand(eqn, ndim, coordinate_symbol, substitutions, constants))

block = SimulationBlock(ndim, block_number=0)

weno_order = '5Z'
Euler_eq = EulerEquations(ndim)
ev_dict, LEV_dict, REV_dict = Euler_eq.generate_eig_system()
Avg = RoeAverage([0, 1], ndim)
LLF = LLFWeno(ev_dict, LEV_dict, REV_dict, weno_order, ndim, Avg)

schemes = {}
schemes[LLF.name] = LLF
cent = Central(4)
schemes[cent.name] = cent
rk = RungeKutta(3)
schemes[rk.name] = rk

boundaries = []
for direction in range(ndim):
    boundaries += [PeriodicBoundaryConditionBlock(direction, 0)]
    boundaries += [PeriodicBoundaryConditionBlock(direction, 1)]

block.set_block_boundaries(boundaries)
block.set_discretisation_schemes(schemes)
# Local dictionary for parsing the expressions
local_dict = {"block": block, "GridVariable": GridVariable, "DataObject": DataObject}

# Initial conditions as strings

x0 = "Eq(DataObject(x0), -0.5+block.deltas[0]*block.grid_indexes[0])"
x1 = "Eq(DataObject(x1), -0.5+block.deltas[1]*block.grid_indexes[1])"

name = 'random_nums'
x1c = "Eq(GridVariable(x1c), DataObject(x1))"
d_in = "Eq(GridVariable(d), Piecewise((1.0 ,x1c<-0.25),(1.0, x1c>0.25),(2.0,True)))"
u0_in = "Eq(GridVariable(u0),  Piecewise((-0.5 ,x1c<-0.25),(-0.5, x1c>0.25),(0.5+0.01*(DataObject(random_nums)-0.5),True)))"
u1_in = "Eq(GridVariable(u1),Piecewise((0 ,x1c<-0.25),(0, x1c>0.25),(0.01*(DataObject(%s)-0.5),True)))" % name
p_in = "Eq(GridVariable(p), 2.5)"

rho = "Eq(DataObject(rho), d)"
rhou0 = "Eq(DataObject(rhou0), d*u0)"
rhou1 = "Eq(DataObject(rhou1), d*u1)"
rhoE = "Eq(DataObject(rhoE), p/(gama-1) + 0.5* d *(u0**2+u1**2))"

eqns = [x0, x1, x1c, d_in, u0_in, u1_in, p_in, rho, rhou0, rhou1, rhoE]
initial_equations = [parse_expr(eq, local_dict=local_dict) for eq in eqns]
initial = GridBasedInitialisation()
initial.add_equations(initial_equations)

# Set equations on the block and discretise
block.set_equations([constituent, initial, simulation_eq])
block.discretise()
block.block_datasets['%s_B0' % 'random_nums'].read_from_hdf5 = True

alg = TraditionalAlgorithmRK(block)
SimulationDataType.set_datatype(Double)
OPSC(alg)
# Random number generation for the initial condition
# Change grid size here if desired
halos = [-5, 5]
npoints = [512, 512]
# Generate the initial white noise seeding
random_numbers = np.random.rand(npoints[0]+2*halos[1], npoints[1]+2*halos[1])
output_hdf5(random_numbers, name, halos, npoints, block)
