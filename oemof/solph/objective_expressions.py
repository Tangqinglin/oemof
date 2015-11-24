# -*- coding: utf-8 -*-
"""
The module contains different objective expression terms.

@author: Simon Hilpert (simon.hilpert@fh-flensburg.de)
"""
import numpy as np
import logging

def add_opex_var(model, block, ref='output'):
    """ Variable operation expenditure term for linear objective function

    If reference of opex is `output`:

    .. math:: \\sum_e \\sum_t W(e,O(e),t) \\cdot c_{var}(e)

    If reference of opex is `input`:

    .. math:: \\sum_e \\sum_t W(I(e),e,t) \\cdot c_{var}(e)

    Parameters:
    ------------
    model : OptimizationModel() instance
    objs : objects for which term should be set
    uids : corresponding uids
    ref : reference side on which opex are based on
        (e.g. powerplant MWhth -> input or MWhel -> output)

    """
    if block.uids is None:
        block.uids = [obj.uid for obj in block.objs]

    opex_var = {obj.uid: obj.opex_var for obj in block.objs}
    # outputs for cost objs
    if ref == 'output':
        expr = sum(model.w[e, model.O[e][0], t] * opex_var[e]
                   for e in block.uids
                   for t in model.timesteps)

    elif ref == 'input':
        expr = sum(model.w[model.I[e], e, t] * opex_var[e]
                   for e in block.uids
                   for t in model.timesteps)
    return(expr)

def add_input_costs(model, block):
    """ Adds costs for usage of input (fuel, elec, etc. ) if not included in
    opex

    .. math:: \\sum_e \\sum_t W(I(e), e, t) \\cdot c_{input}(e)

    Parameters:
    ------------

    model : OptimizationModel() instance
    objs : objects for which term should be set
    uids : corresponding uids
    """
    if block.uids is None:
        block.uids = [obj.uid for obj in block.objs]

    input_costs = {}
    for e in block.objs:
        if e.__dict__.get('input_costs', None) is not None:
            input_costs[e.uid] = e.input_costs
        else:
            input_costs[e.uid] = e.inputs[0].price
    # outputs for cost objs
    expr = sum(model.w[model.I[e], e, t] * input_costs[e]
               for e in block.uids for t in model.timesteps)

    return(expr)

def add_opex_fix(model, block, ref=None):
    """ Fixed operation expenditure term for linear objective function

    If reference is `output` (e.g. powerplants):

    .. math:: \\sum_e out_{max}(e) \\cdot c_{fix}(e)

    If reference is `capacity` (e.g. storages):

    .. math:: \\sum_e cap_{max}(e) \\cdot c_{fix}(e)

    If investment:

    .. math:: \\sum_e (out_{max}(e) + ADDOUT(e)) \\cdot c_{fix}(e)

    .. math:: \\sum_e (out_{max}(e) + ADDCAP(e)) \\cdot c_{fix}(e)

    Parameters
    ------------

    model : OptimizationModel() instance
    objs : objects for which term should be set
    uids : corresponding uids
    ref : string
        string to check if capex is referred to capacity (storage) or output
        (e.g. powerplant)

    """
    if not block.objs:
        expr=0
        print('No objects defined for adding fixed opex to objective.' +
              'No action taken.')
        return(expr)
    else:
        if block.uids is None:
            block.uids = [obj.uid for obj in block.objs]
        uids_inv = set([obj.uid for obj in block.objs
                       if block.optimization_options.get('investment', False)])
        uids = set(block.uids) - uids_inv

        opex_fix = {obj.uid: obj.opex_fix for obj in block.objs}
        if ref == 'output':
            # installed electrical/thermal output: {'pp_chp': 30000,...}
            out_max = {obj.uid: obj.out_max for obj in block.objs}
            expr = 0
            expr += sum(out_max[e][0] * opex_fix[e] for e in uids)
            expr += sum((out_max[e][0] + block.add_out[e]) * opex_fix[e]
                        for e in uids_inv)
        elif ref == 'capacity':
            cap_max = {obj.uid: obj.cap_max for obj in block.objs}
            expr = 0
            expr += sum(cap_max[e] * opex_fix[e] for e in uids)
            expr += sum((cap_max[e] + block.add_cap[e]) * opex_fix[e]
                           for e in uids_inv)
        else:
            print('No reference defined. Please specificy in `add_opex()`!')
        return(expr)


def add_revenues(model, block, ref='output'):
    """ revenue term for linear objective function

    .. math:: \\sum_e \\sum_t W(e,O(e),t) \\cdot r_{out}(e,t)

    Parameters
    ------------

    model : OptimizationModel() instance
    block : SimpleBlock()
    """

    if block.uids is None:
        block.uids = [obj.uid for obj in block.objs]

    expr = 0
    if ref == 'output':
        #  if price is already a vector (array) this vector is taken
        output_price = {}
        for e in block.objs:
            if e.__dict__.get('output_price', None) is not None:
                if isinstance(e.output_price, (float, int, np.integer)):
                    output_price[e.uid] = output_price * len(model.timesteps)
                else:
                    output_price[e.uid] = e.output_price
            elif isinstance(e.outputs[0].price, (float, int, np.integer)):
                output_price[e.uid] = \
                    [e.outputs[0].price] * len(model.timesteps)
            else:
                output_price[e.uid] = e.outputs[0].price

        # create expression term
        expr += -sum(model.w[e, model.O[e][0], t] * output_price[e][t]
                     for e in block.uids for t in model.timesteps)
    else:
        pass

    return(expr)

def add_curtailment_costs(model, block=None, objs=None):
    """ Cost term for dispatchable sources in linear objective.

    .. math:: \\sum_e \\sum_ t CURTAIL(e,t) \\cdot c_{curt}(e)

    Parameters
    ------------

    model : OptimizationModel() instance
    objs : objects for which term should be set
    uids : corresponding uids
    """

    if not block.objs:
        expr = 0
        logging.warning('No objects for curtailment costs term in objective' +
        ' defined. No action taken.')
        return(expr)

    else:
        if block.uids is None:
            block.uids = [obj.uid for obj in block.objs]
        # get dispatch expenditure for renewable energies with dispatch
        c_curtail = {obj.uid: obj.curtail_costs for obj in block.objs}
        expr = sum(block.curtailment_var[e, t] * c_curtail[e]
                   for e in block.uids for t in model.timesteps)
    return(expr)

def add_capex(model, block, ref='output'):
    """ Add capital expenditure to linear objective.

    If reference is `output` (e.g. powerplants):

    .. math:: \\sum_e ADDOUT(e) \\cdot crf(e) \\cdot c_{inv}(e)

    If reference is `capacity` (e.g. storages):

    .. math:: \\sum_e ADDCAP(e) \\cdot crf(e) \\cdot c_{inv}(e)

    Parameters
    ------------

    model : OptimizationModel() instance
    objs : objects for which term should be set
    uids : corresponding uids
    ref : string
        string to check if capex is referred to capacity (storage) or output
        (e.g. powerplant)

    """
    if not block.objs:
        expr = 0
        print('No objects for capex objective term defined. No action taken')
        return(expr)
    else:
        if block.uids is None:
            block.uids = [obj.uid for obj in block.objs]

        c_inv = {obj.uid: obj.capex for obj in block.objs}
        crf = {obj.uid: obj.crf for obj in block.objs}

        if ref == 'output':
            expr = sum(block.add_out[e] * crf[e] * c_inv[e]
                       for e in block.uids)
            return(expr)
        elif ref == 'capacity':
            expr = sum(block.add_cap[e] * crf[e] * c_inv[e]
                       for e in block.uids)
            return(expr)
        else:
            print('No reference defined. Please specificy in `add_capex()`')


def add_startup_costs(model, block):
    """ Adds startup costs for components to objective expression

    .. math:: \\sum_{e} \\sum_{t} Z_{start}(e,t) \\cdot c_{start}(e)

    Parameters
    ------------

    model : OptimizationModel() instance
    block : SimpleBlock()

    Returns:
    ---------
    Expression
    """
    if block.objs is None:
        expr = 0
    else:
        if block.uids is None:
            block.uids = [obj.uid for obj in block.objs]

        c_start = {obj.uid: obj.start_costs for obj in block.objs}
        expr = sum(block.z_start[e, t] * c_start[e]
                   for e in block.uids for t in model.timesteps)
    return(expr)

def add_shutdown_costs(model, block):
    """ Adds shutdown costs for components to objective expression

    .. math:: \\sum_{e} \\sum_t Z_{stop}(e,t) \\cdot c_{stop}(e)

    Parameters
    ------------

    model : OptimizationModel() instance
    block : SimpleBlock()
    """

    if block.uids is None:
        block.uids = [obj.uid for obj in block.objs]

    c_stop = {obj.uid: obj.stop_costs for obj in block.objs}
    expr = sum(block.z_stop[e, t] * c_stop[e]
               for e in block.uids for t in model.timesteps)
    return(expr)

def add_ramping_costs(model, block, grad_direc='positive'):
    """ Add gradient costs for components to linear objective expression.

    .. math::  \\sum_e \\sum_t GRADPOS(e,t) \\cdot c_{ramp,neg}(e)

    .. math:: \\sum_e \\sum_t GRADNEG(e,t) \\cdot c_{ramp,pos}(e)

    Parameters
    ------------

    model : OptimizationModel() instance
    block : SimpleBlock()
    grad_direc : string
        direction of gradient for which the costs are added to the objective
        expression

    """
    if block.uids is None:
        block.uids = [obj.uid for obj in block. objs]

    c_ramp = {obj.uid: obj.ramp_costs.get(grad_direc, obj.ramp_costs)
              for obj in block.objs}
    if grad_direc == 'positive':
        expr = sum(block.grad_pos_var[e, t] * c_ramp[e]
                   for e in block.uids for t in model.timesteps)
    if grad_direc == 'negative' :
        expr = sum(block.grad_neg_var[e, t] * c_ramp[e]
                   for e in block.uids for t in model.timesteps)
    else:
        pass
    return(expr)

def add_excess_slack_costs(model, block):
    """ Artificial cost term for excess slack variables.

    .. math:: \\sum_e \\sum_t EXCESS(e,t) \\cdot c_{excess}(e)

    Parameters:
    ------------

    uids : unique ids of bus objects
    """

    c_excess = {b.uid:b.excess_costs for b in block.objs
                if b.excess==True}
    expr = sum(block.excess_slack[e, t] * c_excess[e]
               for e in block.excess_uids for t in model.timesteps)
    return(expr)


def add_shortage_slack_costs(model, block=None):
    """ Artificial cost term for shortage slack variables.

    .. math:: \\sum_e \\sum_t SHORTAGE(e,t) \\cdot c_{shortage}(e)

    Parameters:
    ------------

    """
    c_shortage = {b.uid: b.shortage_costs for b in block.objs
                  if b.shortage==True}
    expr = sum(block.shortage_slack[e, t] * c_shortage[e]
               for e in block.shortage_uids for t in model.timesteps)
    return(expr)


