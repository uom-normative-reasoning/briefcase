import argparse
import yaml
import networkx as nx

from enum import Enum
from pathlib import Path
from collections import defaultdict

decision = Enum('Decision', ['pi', 'delta', 'un'])

class Factor:
    def __init__(self, name, polarity='un'):
        self.name = name
        self.polarity = polarity
    
    def __eq__(self, other):
        if type(other) is type(self):        
            return self.name == other.name and self.polarity == other.polarity
        else:
            return False

    def __hash__(self):
        return hash(self.name+str(self.polarity))

class Case:

    @classmethod
    def from_dict(cls, dic):
        # Should do sanity check e.g., that reason is a subset of the winning factors.
        return cls(frozenset({Factor(f, decision.pi) for f in dic['pi']}), 
                frozenset({Factor(f, decision.pi) for f in dic['delta']}), 
                decision[dic['decision']], 
                frozenset({Factor(f, decision.pi) for f in dic['reason']}))
    
    def __init__(self, pi_factors=frozenset(), delta_factors=frozenset(), decision=decision.un, reason=frozenset()):
        '''I think we can have as a degenerate case a pure decision, that is, one with no factors
        and thus no reasons. Alternatively, we could force all such to be undecided.
        
        If we allow nominal typing, then degenerate cases can be meaninfully different. We might use
        a general rule to express burden of proof, e.g., that we default for the defense.
        
        We might want to have an additional typology of cases to allow different burden of proofs for 
        different sorts of cases, e.g., civil vs. criminal.'''
        
        self.pi_factors = pi_factors
        self.delta_factors = delta_factors
        self.decision = decision
        self.reason = reason
    
    def defeated(self): #TODO: make property
        if self.decision == decision.pi:
            return self.delta_factors
        elif self.decision == decision.delta:
            return self.pi_factors
        else:
            return set() #TODO: Throw error?
    
    def relevant_diff_from(self, other_case):
        """All factors have a singleton dimension and thus
        any individual factor"""
        if self.decision == other_case.decision:
            pass
class PriorityOrder:
    def __init__(self):
        self.order = defaultdict(set)

    def is_consistent(self):
        for U, Vs in list(self.order.items()): #Honestly no idea! What am I changing below?! Copy doesn't work!
            for V in Vs:
                # We know U > V. Check for reverse!
                for u in self.order[V]:
                    if U.issubset(u): #i.e., U < u, since then U < V since  u < V and subset rule
                        return False
        return True
    
    def is_consistent_with(self, case):
        assert self.is_consistent() #TODO: is this what we want?
        
        reason = case.reason
        defeated = case.defeated()
        # It's only one step, so we don't have to chase long cycles.
        for U in [self.order[r] for r in self.order.keys() if r.issubset(defeated)]:
            for u in U:
                if reason.issubset(u):
                    return False
        return True

    def add_pair_as_appropriate(self, r1, r2):
        if r1 == r2:
            return
        if r1.issubset(r2):
            # Potentially a bit slow for large reasons? could check for polarity first.
            self.order[r2].add(r1)
            #ds has to be of opposite polarity thus disjoint from the reason
        elif r2.issubset(r1):
            self.order[r1].add(r2)
 
    def unsafe_add_cases(self, cases):
        for c in cases:
            self.unsafe_add_case(c)    
            
    def unsafe_add_case(self, case):
        '''Adds the decision with no safety checks.'''        
        self.order[case.reason].add(case.defeated())  
        for r, ds in list(self.order.items()):
            self.add_pair_as_appropriate(case.reason, r)
            # Because we don't do a polarity check, we have to test *all* ds...boo)
            for d in ds:
                self.add_pair_as_appropriate(case.reason, d)
    
    def newly_inconsistent_with(self, case):
        pass
           
    def inconsistent_pairs(self):
        pass
    
class NXPriorityOrder:
    def __init__(self):
        self.order = nx.DiGraph()
    
    def is_consistent(self):
        pass
    
    def is_consistent_with(self, case):
        reason = case.reason
        defeated = case.defeated()
    
    def newly_inconsistent_with(self, case):
        pass
    
    def add_case(self, case):
        '''Adds the decision with no safety checks.'''
        reason = case.reason
        defeated = case.defeated()
        self.order.add_edge(reason, defeated(), case=case) #TODO: add attribute
        # A reason is *at least as strong* than any subset of the reason
        for n in self.order.nodes:
            if n.issubset(reason):
                self.order.add_edge(reason, n, type="superset")
            if n.issubset(defeated):
                self.order.add_edge(defeated, n, type="superset")
        
    def inconsistent_pairs(self):
        pass

class CaseBase:
    def __init__(self, caselist=[]):
        self.cases = caselist
        self.order = PriorityOrder()
        self.order.unsafe_add_cases(self.cases)
    
    def add_case(self, case):
        self.cases.append(case)
        self.order.unsafe_add_case(case)
        
    def is_consistent(self):
        return self.order.is_consistent()
    
    def is_consistent_with(self, case):
        return self.order.is_consistent_with(case)
                

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='A tool to do precedential case reasoning.')
    parser.add_argument('-c', '--casebase', type=Path,
                    help='a file containing a case base')
    parser.add_argument('-n', '--newcase', type=Path, 
                    help='file containing a case not in the base')
    parser.add_argument('-a', '--action', type=str, default='test', 
                        help='indicates the preferred action: "check" (default), or "add" (if consistent) or "test" (default) for run tests')

    args = parser.parse_args()
    
    import doctest
    doctest.testfile('example_tests.txt')
    
    #cases = list()
    #for c in yaml.safe_load(args.casebase.read_text()):
        #cases.append(Case.from_dict(c))
    #cb = CaseBase(cases)
    #c = yaml.safe_load('''name: case3
#pi: [p1,p3,p7]
#delta: [d5, d2, d3]
#decision: pi
#reason: [p1,p3,p7]''')
    #tc = Case.from_dict(c)
    #print("CB consistent?", cb.order.is_consistent())
    #print("Consistent with?", cb.is_consistent_with(tc))
    #cb.add_case(tc)
    #print("Consistent if we add it?", cb.order.is_consistent())
