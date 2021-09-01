
"""
The city data was obtained by merging information from: http://www.tageo.com/index-e-as-cities-AU.htm
with data from https://en.wikipedia.org/wiki/List_of_cities_in_Australia_by_population
and individual Wikipedia pages for the cities.
The map was obtained from: https://www.google.com.au/maps
"""

import matplotlib.pyplot as plt
import imageio as im
import matplotlib.animation as animation
import sys
import datetime
import os
from matplotlib import gridspec

########################################################################################################################
#                               Simulation settings
########################################################################################################################
"""
    There are six different simulations that are 'built in' 
    They essentially change the parameters and initial setup (such as where the outbreak starts).
    You can change the simulation being run by changing the SIMULATION_NUMBER constant.
    0: the default - this is the default simulation settings, and also the settings used for the unit-testing.
    1 - 3: Other simulations you can explore
    4: is the simulation you should use to answer question 4
    Once you choose the simulation number, all the other parameters will be set accordingly.
"""
########################################################################################################################
#                           Change this to run a different simulation
SIMULATION_NUMBER = 3  # An integer from 0 to 4 corresponding to the particular simulation we are running
########################################################################################################################


#  Map coordinates
MAP_LEFT = 112.2
MAP_RIGHT = 154.3
MAP_TOP = -10.3
MAP_BOTTOM = -40.2

# These parameters will be set by choosing the simulation number. They are all constant for a particular simulation.
STOPPING_CONDITIONS = 0  # An integer 0 - run to completion, otherwise an integer > 0 to describe the number of turns.
TREATMENT_MOVEMENT = False  # A boolean: False means the treatment centres are stationary, True means they move.
TREATMENT_LIMIT = 0  # The maximum number of infected a treatment unit can deal with.
MORTALITY_RATE = 1.0  # The proportion of infected people who die (float between 0 and 1.0).
INFECTION_RATE = 4.0  # The spreading factor. The number of new cases per infected per step (float >= 0).
MOVEMENT_PROPORTION = 0.1  # The proportion of infected who move cities each step (float between 0 and 1).
AVERAGE_DURATION = 4.0  # The average number of turns to recover or die, (float > 0).


########################################################################################################################
#                                            Logger Class
########################################################################################################################

class Logger(object):
    """ Class for logging key events from the simulation and writing them into a text file """
    def __init__(self):
        """ Creates a logging directory if there isn't one there already and opens a log file """
        if not os.path.exists(os.path.join(os.getcwd(), "logs")):
            os.mkdir(os.path.join(os.getcwd(), "logs"))

        self.log_file = open(os.path.join(os.getcwd(), "logs", "Log_{}.txt".format(
        str(datetime.datetime.now()).replace(":", "_"))), mode="w")
    
    def log(self,message):
        """ Logs an INFO entry with the passed message """
        self.log_file.write("# INFO - {} \n".format(message))

    def close(self):
        """ Closes the text file """
        self.log_file.close()

########################################################################################################################
#                                            City Class
########################################################################################################################

class City(object):
    """ Basic class for modelling a population centre. """

    def __init__(self, lat, long, name, population):
        """
        Initialises the instance
        :param lat: latitude of the city
        :param long: longitude of the city
        :param name: name of the city
        :param population: population of the city
        """

        self.name = name
        self.lat = lat
        self.long = long
        self.infected = 0
        self.incoming_infected = 0
        self.survivors = 0
        self.cured = 0
        self.dead = 0
        self.initial_population = population
        self.healthy_population = population
        self.neighbours = set()  # These are other instances of the city class.
        self.ever_infected = False

    def __hash__(self):
        """ Returns a hash value of the city name to be used in Sets and Dict """
        return hash(self.name)

    def __ne__(self, other):
        """ Returns False if the two cities in both sides of the == operator have the same name """
        return self.name != other.name
    
    def __eq__(self, other):
        """ Returns True if the two cities in both sides of the == operator have the same name """
        return self.name == other.name

    def __lt__(self, other):
        """ Returns boolean of the given comparison statement"""
        return self.name < other.name

    def add_neighbour(self, neighbour):
        """ Adds a connection between the city and the passed neighbour """
        self.neighbours.add(neighbour)

    def remove_neighbour(self, neighbour):
        """ Closes the connection between the city and the passed neighbour """
        self.neighbours.remove(neighbour)
    
    ## Functions used to inspect the city metrics.
    def first_case(self):
        """ Returns True when the first infected case is recorded """
        # Tests if the city has ever been infected before
        if self.ever_infected == False and self.infected > 0:
            self.ever_infected = True
            return True
        else:
            return False

    def infection_free(self):
        """ Return True when infected cases drop to zero """
        if self.ever_infected == True and self.infected == 0:
            return True
        else:
            return False

    def all_infected(self):
        """ Returns True if the entire population is infected """
        if self.initial_population <= self.infected and self.infected != self.dead:
            return True
        else:
            return False

    ## Functions to run the simulation on the city for each turn
    def start_of_turn(self):
        """ Incorporates the arrival of new infected population to the city """
        self.infected += self.incoming_infected
        self.incoming_infected = 0

    def run_turn(self, turn_number):
        # Each turn:

        # A proportion of infected cases move to a neighbouring city
        self.move_infected()

        # Then a proportion of infected cases either die or recover
        # The minimum number of infected cases that either die or recover is 5 (or all cases if less than 5 infected).
        self.change_in_infected_numbers()

        # Each remaining infected case contacts other people based on infection rate.
        # - if the contact is a survivor or has been cured, nothing happens.
        # - if the contact a healthy person, they get the disease.
        # - if there are less than 10 infected people and no healthy people in the city, set the number of infected to 0.
        self.spread_infection()


    def move_infected(self):
        if len(self.neighbours) <= 0:
            return
        cases_moving = int(self.infected * MOVEMENT_PROPORTION)
        cases_per_neighbour = cases_moving // len(self.neighbours)

        for nbr in self.neighbours:
            nbr.incoming_infected += cases_per_neighbour
            self.infected -= cases_per_neighbour

    def change_in_infected_numbers(self):
        """ applies the simulation rules and updates the tolls of the population between still
                infected, survived (recovered) or died"""
        if self.infected > 5:
            cases_resolved = max(int(self.infected // AVERAGE_DURATION), 5)
        elif self.infected > 0:
            cases_resolved = self.infected
        else:
            cases_resolved = 0
        cases_die = int(cases_resolved * MORTALITY_RATE)

        self.infected -= cases_resolved
        self.survivors += (cases_resolved - cases_die)
        self.dead += cases_die

    def spread_infection(self):
        if self.healthy_population + self.survivors + self.cured > 0:

            r = self.healthy_population / (self.healthy_population + self.survivors + self.cured)
            hc = int(r * self.infected * INFECTION_RATE)

            if self.healthy_population < hc:
                self.infected += self.healthy_population
                self.healthy_population = 0

            elif self.infected > 0:
                self.healthy_population -= hc
                self.infected += hc

        if self.infected < 10 and self.healthy_population == 0:
            self.dead += int(self.infected * MORTALITY_RATE)
            self.survivors += (self.infected - int(self.infected * MORTALITY_RATE))
            self.infected = 0

    ####################################################################################################################
    #                                      FOR SIMULATION NUMBER 4
    ######################## Reseting the city metrics after the simulation runs #######################################

    def reset(self):
        self.infected = 0
        self.incoming_infected = 0
        self.survivors = 0
        self.cured = 0
        self.dead = 0
        self.healthy_population = self.initial_population
        self.ever_infected = False
        
    def get_neighbours(self):
        return [n for n in self.neighbours]
        

########################################################################################################################
#                                          Treatment Centre Class
########################################################################################################################
class TreatmentCentre(object):
    """ Class for a treatment for the pandemic (cure for the virus, etc."""

    def __init__(self, treatment_id, city, logger=None):
        """
        :param treatment_id: The id of the TreatmentCentre
        :param city: The city where it is located (instance of the City class).
        """

        self.treatment = treatment_id
        self.treatment_remaining = TREATMENT_LIMIT
        self.city = city
        self.logger = logger

    def find_most_affected_city(self):
        """ Returns the neighbouring city with the most infected cases """
        most_affected_city = self.city
        most_infected_cases = self.city.infected

        for neighbour in self.city.neighbours:
            if neighbour.infected > most_infected_cases:
                most_affected_city = neighbour
                most_infected_cases = neighbour.infected
        return most_affected_city

    def move(self):
        """ Moves the treatment centre.
        Looks at neighbouring cities of the current city to find the one with the most
        infected cases and moves there. Should stay where it is if the current city has the most.
        """
        most_affected_city = self.find_most_affected_city()
        
        if self.city != most_affected_city:
            if logger is not None:
                logger.log("Treatment Center with ID {} moved from {} to {}".format(
                    self.treatment, self.city.name, most_affected_city.name))
            self.city = most_affected_city

    def run_turn(self, turn_number):
        """ Runs the turn for the treatment unit.
        If movement is on, tries to move.
        Then treats any infected people in the city.
        """
        if TREATMENT_MOVEMENT:
            self.move()

        if self.city.infected <= self.treatment_remaining:
            self.treatment_remaining -= self.city.infected
            self.city.cured += self.city.infected
            self.city.infected = 0
        else:
            self.city.cured += self.treatment_remaining
            self.city.infected -= self.treatment_remaining
            self.treatment_remaining = 0


########################################################################################################################
#                                                  Engine Class
########################################################################################################################
class Engine(object):
    """ Class to actually run the simulation. """

    def __init__(self, cities, treatments, logger=None):

        self.turn_number = 0
        self.cities = cities
        self.treatments = treatments
        self.logger = logger

        # Attributes for collecting simulation statistics.
        self.healthy_population = []
        self.infected = []
        self.survivors = []
        self.deaths = []
        self.cured = []

    def log_out_city_info(self, city):
        """Logs out three (3) distinctive events:
            1- First case of infection in a city
            2- The city population is infection free
            3- The city population is 100% infected
        """
        if self.logger is not None:
            if city.first_case():
                logger.log("{} recorded its first infected case".format(city.name))
            if city.infection_free():
                logger.log("{}'s population is infection free".format(city.name))
            if city.all_infected():
                logger.log("{}'s population is 100% infected".format(city.name))

    def log_out_turn_info(self):
        logger.log("--------- Turn No. {} aftermath ---------".format(self.turn_number))
        logger.log("Total infections: {}".format(self.infected[-1]))
        logger.log("Total healthy population: {}".format(self.healthy_population[-1]))
        logger.log("Total survivors: {}".format(self.survivors[-1]))
        logger.log("Total deaths: {}".format(self.deaths[-1]))
        logger.log("Total cured: {}".format(self.cured[-1]))
        logger.log("-----------------------------------------")

    def run_turn(self):
        """ Advances the simulation by a single turn."""
        self.turn_number += 1

        if self.logger is not None:
            self.logger.log("Running Turn Number {}".format(self.turn_number))

        # Run the start of turn in each city.
        for city in self.cities.values():
            city.start_of_turn()

        # Run the actual turn in each city.
        for city in self.cities.values():
            city.run_turn(self.turn_number)
            self.log_out_city_info(city)

        # Run the turn for each treatment centre
        for treatment in self.treatments.values():
            treatment.run_turn(self.turn_number)

        # Gather the statistics
        self.infected.append(sum([city.infected for city in self.cities.values()]))
        self.healthy_population.append(sum([city.healthy_population for city in self.cities.values()]))
        self.survivors.append(sum([city.survivors for city in self.cities.values()]))
        self.deaths.append(sum([city.dead for city in self.cities.values()]))
        self.cured.append(sum([city.cured for city in self.cities.values()]))
        
        #Logs out some run_turn stats
        self.log_out_turn_info()


########################################################################################################################
#                                                Other functions
########################################################################################################################
def convert_lat_long(lat, long):
    """ Converts a latitude and longitude pair into an x, y pair of map-coordinates.
    :param lat: the latitude value.
    :param long: the longitude value.
    :return an (x, y) tuple of coordinates, where x and y are floats between 0.0 and 1.0.
    """

    x_diff = MAP_RIGHT - MAP_LEFT
    y_diff = MAP_TOP - MAP_BOTTOM

    return (long - MAP_LEFT) / x_diff, (lat - MAP_BOTTOM) / y_diff


def get_city_data(file_name):
    """ Reads in city and connection data from the specified file.
    Format of the file is:
    lat,long,name,population
    ### - break point between the two sections.
    city_1,city_2
    """

    input_file = open(file_name, mode="r")

    # Get the cities first
    cities = dict()
    for line in input_file:
        # Check for the end of the city information
        if line[0:3] == "###":
            break
        line = line.strip().split(",")

        lat = float(line[0])
        long = float(line[1])
        name = line[2]
        population = int(line[3])
        cities[name] = City(lat, long, name, population)

    # Now read in the connections
    for line in input_file:
        city_1, city_2 = line.strip().split(",")
        cities[city_1].add_neighbour(cities[city_2])
        cities[city_2].add_neighbour(cities[city_1])

    return cities


def get_initial_parameters(scenario_number):
    """
    Gets the initial parameters and treatment options for the given scenario.
    :param scenario_number: The scenario being run.
    :return: a tuple of (stopping, treatment move, treat lim, mortality, infection rt, movement prop, average dur).
    """

    #       Stop    TrtMo   TRtL    MoR     InR     MoP     AvgDur
    scenario_dict = {
        0: (0,      False,  0,      1.0,    4.0,    0.1,    4.0),
        1: (150,    False,  0,      0.1,    0.4,    0.25,   3.0),
        2: (150,    True,   150000, 0.1,    0.4,    0.25,   3.0),
        3: (0,      True,   150000, 0.25,   1.5,    0.1,    4.0),
        4: (20,     False,  0,      0.3,    1.0,    0.05,   4.0)
    }

    if scenario_number not in scenario_dict:
        scenario_number = 0

    return scenario_dict[scenario_number]


def set_initial_state(scenario_number, engine):
    """
    Sets the initial infection cases and treatment centres.
    The initial infection cases are added using the 'incoming_infected' attribute.
    Modifies the state of cities and treatment centres in the engine directly.
    :param scenario_number: The scenario being run.
    :param engine: the engine running the simulation.
    :return: None
    """

    state_dict = {
        0: (tuple(), (("Alice Springs", 1000),)),
        1: (tuple(), (("Rockhampton", 1000), ("Brisbane", 10000), ("Gold Coast", 1000))),
        2: (("Sydney", "Melbourne", "Adelaide"), (("Rockhampton", 1000), ("Brisbane", 10000), ("Gold Coast", 1000))),
        3: (("Sydney", "Perth", "Melbourne"), (("Canberra", 5000), ("Cairns", 5000))),
        4: (tuple(), (("Rockhampton", 1000), ("Brisbane", 10000), ("Gold Coast", 1000)))
    }

    if scenario_number not in state_dict:
        scenario_number = 0

    for index, city in enumerate(state_dict[scenario_number][0]):
        engine.treatments[index] = TreatmentCentre(index, engine.cities[city],engine.logger)

    for city, cases in state_dict[scenario_number][1]:
        engine.cities[city].incoming_infected = cases


def animate_map(data, engine, map_image, sp1, sp2, sp3, sp4):

    if not engine:
        return

    # Check for termination conditions here.
    if (engine.infected and engine.infected[-1] == 0) or (STOPPING_CONDITIONS and
                                                          engine.turn_number >= STOPPING_CONDITIONS):
        get_input = input("The simulation has ended; press 'Enter' to finish.")
        sys.exit()

    # Advance the simulation by 1 turn
    engine.run_turn()

    # Display the map and statistics
    height, width = len(map_image), len(map_image[0])

    sp1.clear()
    sp1.set_axis_off()
    sp1.imshow(map_image)
    sp1.set_title("Pandemic Simulation - {} turns".format(engine.turn_number))

    # Plot the cities
    for city in engine.cities.values():
        x, y = convert_lat_long(city.lat, city.long)
        if city.infected > 0.1 * city.initial_population:
            color = "red"
        elif city.infected > 0.01 * city.initial_population:
            color = "orange"
        elif city.infected > 0:
            color = "yellow"
        elif city.healthy_population == 0 and city.survivors == 0 and city.cured == 0:
            color = "black"
        else:
            color = "blue"

        sp1.plot(x * width, (1 - y) * height, "o", markersize=10.0, color=color)
        if city.initial_population > 150000:
            sp1.text(x * width + 12, (1 - y) * height + 12, s=city.name)

        # Uncomment the following four lines if you wish to see the connections on the map during simulation.
        #for nbr in city.neighbours:
        #    if nbr < city:
        #        nx, ny = convert_lat_long(nbr.lat, nbr.long)
        #        sp1.plot((x * width, nx * width), ((1 - y) * height, (1 - ny) * height), color="black")

    # Plot the line graphs
    sp2.clear()
    sp2.plot(range(1, engine.turn_number + 1), engine.healthy_population, color="blue", label="Healthy")
    sp2.plot(range(1, engine.turn_number + 1), engine.infected, color="red", label="Infected")
    sp2.set_xlim([1, engine.turn_number + 15])
    sp2.legend(loc="right")
    sp2.set_xlabel("Turns")
    sp2.set_ylabel("People")
    sp2.set_title("Simulation Statistics")
    if (max(engine.healthy_population) > 10 * max(engine.infected) or
            max(engine.healthy_population) * 10 < max(engine.infected)):
        sp2.set_yscale("log")

    sp3.clear()
    sp3.plot(range(1, engine.turn_number + 1), engine.survivors, color="green", label="Survivors")
    sp3.plot(range(1, engine.turn_number + 1), engine.deaths, color="black", label="Deaths")
    sp3.set_xlim([1, engine.turn_number + 15])
    sp3.legend(loc="right")
    sp3.set_xlabel("Turns")
    sp3.set_ylabel("People")
    if (max(engine.survivors) > 10 * max(engine.deaths) or
            max(engine.survivors) * 10 < max(engine.deaths)):
        sp3.set_yscale("log")

    sp4.clear()
    sp4.plot(range(1, engine.turn_number + 1), engine.cured, color="purple", label="Cured")
    sp4.set_xlim([1, engine.turn_number + 15])
    sp4.legend(loc="right")
    sp4.set_xlabel("Turns")
    sp4.set_ylabel("People")

####################################################################################################################
#                                SIMULATION 4 - OTHER FUNCTIONS
####################################################################################################################
SIMULATION_ITERATIONS = 20

def run_simulations_get_deaths(cities):
    # Reset the cities metrices to initial state
    reset_cities(cities)
    temp_treatments = dict()
    temp_engine = Engine(cities, temp_treatments)
    set_initial_state(SIMULATION_NUMBER, temp_engine)
    for _ in range(SIMULATION_ITERATIONS):
        temp_engine.run_turn()
    return temp_engine.deaths[-1]

def reset_cities(cities):
    for city in cities.values():
        city.reset()

def find_best_config(cities):
    minimum_deaths = float('inf')
    minimum_deaths_config = dict()  #City,neighbour configuration with the minimum deaths
    
    #remove the first connection
    for city1 in cities.values():
        for neighbour1 in city1.get_neighbours():
            city1.remove_neighbour(neighbour1)
            #remove the second connection
            for city2 in cities.values():
                for neighbour2 in city2.get_neighbours():
                    city2.remove_neighbour(neighbour2)            
                    #remove the third connection
                    for city3 in cities.values():
                        for neighbour3 in city3.get_neighbours():
                            city3.remove_neighbour(neighbour3) 

                            deaths = run_simulations_get_deaths(cities)
                            if deaths < minimum_deaths:
                                minimum_deaths = deaths
                                minimum_deaths_config = {city1:neighbour1,city2:neighbour2,city3:neighbour3}
                                print("minimum:{} config: {}->{} , {}->{}, {}->{}".format(
                                                    minimum_deaths,city1.name,neighbour1.name
                                                    ,city2.name,neighbour2.name
                                                    ,city3.name,neighbour3.name
                                                    )
                                )
                            city3.add_neighbour(neighbour3)
                    city2.add_neighbour(neighbour2)
            city1.add_neighbour(neighbour1)
            
    return minimum_deaths_config
########################################################################################################################
#                                         Main Function
########################################################################################################################
if __name__ == "__main__":

    logger = Logger()
    logger.log("************ Simulation Number {} ************".format(SIMULATION_NUMBER))

    # Set the scenario parameters
    STOPPING_CONDITIONS, TREATMENT_MOVEMENT, TREATMENT_LIMIT, MORTALITY_RATE, \
        INFECTION_RATE, MOVEMENT_PROPORTION, AVERAGE_DURATION = get_initial_parameters(SIMULATION_NUMBER)

    # Get the city data and population
    cities = get_city_data("final_city_data.csv")
    treatments = dict()

    # Create the engine that will run the simulation
    engine = Engine(cities, treatments, logger)

    # Setup initial infected cases and treatment centres
    set_initial_state(SIMULATION_NUMBER, engine)

    ####################################################################################################################
    # The road closures will occur between Rockhampton --> Mackay, Brisbane --> Toowomba, Brisbane --> Sunshine Coast
    # from the start would prevent massive spreading of the disease in other cities.
    #
    ####################################################################################################################
    if SIMULATION_NUMBER == 4:
        # Go through every possible combination of 3 closed road connections
        # and calculate the death toll after 20 iterations
        # return the 3 connections that give the smallest death toll
        minimum_deaths_config = find_best_config(cities)
        
        # Reset the cities metrics
        reset_cities(cities)
        set_initial_state(SIMULATION_NUMBER, engine)
        for city,neighbour in minimum_deaths_config.items():
            cities[city.name].remove_neighbour(neighbour)


    ####################################################################################################################

    # Get the map and fade it for better viewing.
    aus_map = im.imread("Aus_Map.PNG")
    aus_map[:,:,3] = (aus_map[:,:,3] * 0.6)

    # Setup the plot layout
    fig = plt.figure(figsize=[10, 13])
    sps1, sps2, sps3, sps4 = gridspec.GridSpec(4, 1, height_ratios=(10, 1, 1, 1))

    sp1 = plt.subplot(sps1)
    sp2 = plt.subplot(sps2)
    sp3 = plt.subplot(sps3)
    sp4 = plt.subplot(sps4)

    # Produce the animation and run the simulation.
    display = animation.FuncAnimation(fig, animate_map, interval=100, repeat=False,
                                      fargs=(engine, aus_map, sp1, sp2, sp3, sp4),
                                      frames=None)
    plt.show()
    logger.close()
    
