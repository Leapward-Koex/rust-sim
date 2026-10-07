from dicty_sim_test_env import variables
from locus import Locus

# Simulation
class Cell:
    _id_counter = 0  # Class attribute to keep track of the last ID assigned

    def __init__(self, positionX, positionY, fitness, mating_type, spore_chance, loci_list):
        self.loci = loci_list
        self.positionX = positionX
        self.positionY = positionY
        self.fitness = fitness
        self.mating_type = mating_type
        self.spore_chance = spore_chance

        self.key = Cell._id_counter
        Cell._id_counter += 1
    
    def __str__(self):
        return f"{self.key}"
    
    def __repr__(self):
        return f"{self.key}"
    
    def __eq__(self, other):
            if isinstance(other, Cell):
                return self.key == other.key
            return False
    def clone(self):
        # This function is needed to ensure each time a cell is duplicated it is assigned a new spot in memory - without it duplicated cells
        # point to the same object and a change to one changes all
        new_loci_list = [Locus(locus.cheater_allele, locus.resistor_allele) for locus in self.loci]
        return Cell(self.positionX, self.positionY, self.fitness, self.mating_type, self.spore_chance, new_loci_list)
    
    def __hash__(self):
        return hash(self.key)

    def cheater_value(self):
        value = 0
        for locus in self.loci:
            value += locus.cheater_allele
        return value

    def wild_value(self):
        value = 0
        for locus in self.loci:
            if locus.cheater_allele == 0:
                value += 1
            if locus.resistor_allele == 0:
                value += 1
        return value

    def resistor_value(self):
        value = 0
        for locus in self.loci:
            value += locus.resistor_allele
        return value

    def ch_eff(self):

        # Effectiveness of a single loci
        single_loci_value = 1/len(self.loci)

        # Count how many loci have both alleles present
        both_alleles = 0
        for locus in self.loci:
            both_alleles += locus.both()

        # Overall ch effectiveness is equal to # loci with only ch allele times single loci effect, plus (# loci with both weighted by ch_eff_rc)
        eff = ((self.cheater_value()-both_alleles)*single_loci_value)+((both_alleles*variables["ch_eff_rc"])*single_loci_value)
        return eff

    def res_eff(self):
        # Effectiveness of a single loci
        single_loci_value = 1/len(self.loci)

        # Count how many loci have both alleles present
        both_alleles = 0
        for locus in self.loci:
            both_alleles += locus.both()

        # Overall ch effectiveness is equal to # loci with only ch allele times single loci effect, plus (# loci with both weighted by ch_eff_rc)
        eff = ((self.resistor_value()-both_alleles)*single_loci_value)+((both_alleles*variables["res_eff_rc"])*single_loci_value)
        return eff
    
    def exploitable(self, other):

        #If the cheater allele is invalidated by co-occurence
        if variables["ch_eff_rc"] == 0:
            for index in range(0, len(self.loci)):
                if self.loci[index].both() == 1 or self.loci[index].cheater_allele == 0: #Check if there is co-occurence (invalidates ch allele) or if there is no cheater allele
                    continue # If cant cheat at this gene pair, go to next pair
                elif variables["res_eff_rc"] == 0: # If resistance allele is invalidated by co-occurence
                    if other.loci[index].cheater_allele == 1 and other.loci[index].both() == 0: # First check if the other cell has an active cheater allele at this pair
                        continue # If it does, cant cheat go to next pair
                    elif other.loci[index].both() == 1 or other.loci[index].resistor_allele == 0: # Check if other cell has co-occurence or no resistor (same thing here)
                        return 1 # If it does, this cell can cheat the other. Return 1 and exit
                elif variables["res_eff_rc"] == 1: # If the resistance allele does not have epistasis
                    if other.loci[index].cheater_allele == 1 and other.loci[index].both() == 0: # Check if the toher cell has an active cheater allele
                        continue # This pair cant be cheated, go to next pair
                    elif other.loci[index].resistor_allele == 0: #If the other cell does not have a resistor allele, can cheat.
                        return 1   
                 
        elif variables["ch_eff_rc"] == 1: #If epsistasis does not occur for cheater allele
            for index in range(0, len(self.loci)):
                if self.loci[index].cheater_allele == 0: # If this pair does not have a cheater allele
                    continue # Go to next pair, this pair cant cheat
                elif variables["res_eff_rc"] == 0: #If 
                    if other.loci[index].cheater_allele == 1:
                        continue
                    elif other.loci[index].both() == 1 or other.loci[index].resistor_allele == 0:
                        return 1
                elif variables["res_eff_rc"] == 1:
                    if other.loci[index].cheater_allele == 1:
                        continue
                    elif other.loci[index].resistor_allele == 0:
                        return 1  
                
        return 0 
                

