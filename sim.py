import simpy                              # SimPy wird für die ereignisbasierte Simulation verwendet
import numpy as np                       # NumPy für Zufallszahlen und numerische Operationen
import matplotlib.pyplot as plt          # Matplotlib zur Visualisierung der Ergebnisse
from multiprocessing import Pool, cpu_count  # Für parallele Ausführung mehrerer Simulationen


class Simulation:
    # Konstante Anzahl an Studenten, die Waschgelegenheiten benötigen
    TOTAL_NUMBER_STUDENTS = 170

    # Durchschnittlich eine Wäsche pro Woche pro Student → umgerechnet auf Minuten
    WASHES_PER_WEEK = 1/7

    # Simulationsdauer in Tagen
    SIMULATION_NUMB_DAYS = 1000

    # Geöffnete Stunden pro Tag (z. B. 14:00–20:00 = 6 Stunden → 360 Minuten)
    SIMULATION_HOURS_PER_DAY = 6

    def __init__(self, number_washing_machines, number_dryers):
        # Setze Maschinenanzahl dynamisch
        self.NUMBER_WASHING_MACHINES = number_washing_machines
        self.NUMBER_DRYERS = number_dryers

        # Starte Simulation
        self.simulate()

    def simulate(self):
        # Initialisiere Logdaten zur späteren Auswertung
        self.log = {
            "washing_machine_finished": 0,  # erfolgreiche Waschgänge
            "n": 0,                         # Anzahl Studenten, die Waschen wollten
            "dryer_finished": 0,           # erfolgreiche Trocknergänge
            "dryer_n": 0                   # Anzahl Studenten, die trocknen wollten
        }

        # Simuliere jeden Tag einzeln
        for day in range(0, self.SIMULATION_NUMB_DAYS):
            env = simpy.Environment()

            # Definiere Ressourcen: Waschmaschinen und Trockner
            ressource_washing_machine = simpy.Resource(env, capacity=self.NUMBER_WASHING_MACHINES)
            ressource_dryer = simpy.Resource(env, capacity=self.NUMBER_DRYERS)

            # Starte täglichen Waschbetrieb
            env.process(self.simulate_day(env, ressource_washing_machine, ressource_dryer))

            # Uncomment für Debug-Ausgabe pro Tag
            # print(f"")
            # print(f"\t{day+1}. Tag")
            # print(f"--------------------------------------------------------")

            env.run()  # Führe Tages-Simulation aus

    def to_timestamp(self, now):
        # Hilfsfunktion für Zeitformatierung in HH:MM (für spätere Print-Debug-Ausgaben)
        return f"{(12 + now // 60):.0f}:{now % 60:02.0f} |\t"

    def simulate_day(self, env, ressource_washing_machine, ressource_dryer):
        students = []  # Liste aller Studenten, die am Tag versucht haben zu waschen

        # Solange Zeit im Waschraum verbleibt (6h = 360min)
        while env.now < self.SIMULATION_HOURS_PER_DAY * 60:
            # Erzeuge Studenten mit Wahrscheinlichkeit abhängig von Gesamtanzahl und Bedarf
            while np.random.randint(0, 101) <= round(
                (self.TOTAL_NUMBER_STUDENTS * self.WASHES_PER_WEEK / (self.SIMULATION_HOURS_PER_DAY * 60)) * 100
            ):
                self.log["n"] += 1  # Zähle jeden Waschversuch

                # Wenn alle Waschmaschinen belegt sind → Student geht wieder
                if len(ressource_washing_machine.users) >= ressource_washing_machine.capacity:
                    # print(f"{self.to_timestamp(env.now)}Student ist gekommen und wieder gegangen da keine Waschmaschine frei ist")
                    continue

                # Erzeuge neuen Student und simuliere Waschvorgang
                # print(f"{self.to_timestamp(env.now)}Student {students[student_index].id} ist gekommen und belädt eine Waschmaschine")
                students.append(Simulation.Student(simulation=self, id=len(students)))
                env.process(students[-1].does_laundry(env, ressource_washing_machine, ressource_dryer))

            # print(f"{self.to_timestamp(env.now)}")
            yield env.timeout(1)  # Simuliere 1 Minute

    class WashingMachine:
        # Verschiedene Waschprogramme mit Dauer und Wahrscheinlichkeit
        _modes = [
            {"name": "Feinwäsche", "time": 90, "probability": 10},
            {"name": "Baumwolle", "time": 150, "probability": 70},
            {"name": "Baumwolle mit Einweichen", "time": 240, "probability": 20}
        ]

        def __init__(self):
            self.mode = ""
            self.time = ""

            # Wähle Waschmodus per Wahrscheinlichkeit aus
            while self.mode == "":
                for mode in self._modes:
                    if mode["probability"] >= np.random.randint(0, 101):
                        self.mode = mode["name"]
                        self.time = mode["time"]
                        break

    class Dryer:
        # Wahrscheinlichkeit, dass ein Student den Trockner benutzt
        probability_usage = 40

        # Verschiedene Trocknerprogramme
        _modes = [
            {"name": "Schanktrocken", "time": 90, "probability": 66},
            {"name": "Extra trocken", "time": 120, "probability": 33}
        ]

        def __init__(self):
            self.mode = ""
            self.time = ""

            # Wähle Trocknerprogramm per Zufall
            while self.mode == "":
                for mode in self._modes:
                    if mode["probability"] >= np.random.randint(0, 101):
                        self.mode = mode["name"]
                        self.time = mode["time"]
                        break

    class Student:
        # Parameter für Zeit, bis Student zurückkehrt zur Maschine
        _get_time_mu = 17
        _get_time_sigma = 6

        _load_unload_time = 2  # Zeit zum Ein-/Ausladen der Wäsche

        def __init__(self, id, simulation):
            self.id = id
            self.simulation = simulation

            self.washing_machine = Simulation.WashingMachine()
            self.get_time_washing_machine = max(
                np.random.normal(self._get_time_mu, self._get_time_sigma), 0
            )

            # Entscheide, ob Trockner genutzt wird
            if Simulation.Dryer.probability_usage <= np.random.randint(0, 101):
                self.use_dryer = True
                self.dryer = Simulation.Dryer()
                self.get_time_dryer = max(
                    np.random.normal(self._get_time_mu, self._get_time_sigma), 0
                )
            else:
                self.use_dryer = False

        def does_laundry(self, env, ressource_washing_machine, ressource_dryer):
            # Waschvorgang starten
            with ressource_washing_machine.request() as req:
                yield req
                # print(f"{self.simulation.to_timestamp(env.now)}Student {self.id} startet Waschmaschine ({self.washing_machine.mode})")

                yield env.timeout(self._load_unload_time)

                yield env.timeout(self.washing_machine.time)
                # print(f"{self.simulation.to_timestamp(env.now)}Waschmaschine von Student {self.id} ist fertig")

                yield env.timeout(self.get_time_washing_machine)
                # print(f"{self.simulation.to_timestamp(env.now)}Student {self.id} holt Wäsche aus Waschmaschine")
                yield env.timeout(self._load_unload_time)

                self.simulation.log["washing_machine_finished"] += 1

            if not self.use_dryer:
                # print(f"{self.simulation.to_timestamp(env.now)}Student {self.id} geht")
                return

            self.simulation.log["dryer_n"] += 1

            # Wenn Trockner voll → abbrechen
            if len(ressource_dryer.users) >= ressource_dryer.capacity:
                # print(f"{self.simulation.to_timestamp(env.now)}Student {self.id} kann Trockner nicht benutzen und geht")
                return

            with ressource_dryer.request() as req:
                yield req
                # print(f"{self.simulation.to_timestamp(env.now)}Student {self.id} fängt Wäsche an zu trocknen ({self.dryer.mode})")

                yield env.timeout(self._load_unload_time)

                yield env.timeout(self.dryer.time)
                # print(f"{self.simulation.to_timestamp(env.now)}Student {self.id} ist fertig mit trocknen ({self.dryer.mode})")

                yield env.timeout(self.get_time_dryer)
                # print(f"{self.simulation.to_timestamp(env.now)}Trocker für Student {self.id} ist fertig")
                yield env.timeout(self._load_unload_time)

                self.simulation.log["dryer_finished"] += 1


# Funktion zum Simulieren eines Maschinen-Trockner-Paars
def simulate_pair(n_washing_machine, n_dryer):
    s = Simulation(number_washing_machines=n_washing_machine, number_dryers=n_dryer)

    value = 0
    value += s.log["washing_machine_finished"]
    value += s.log["dryer_finished"]
    value /= (s.log["n"] + s.log["dryer_n"])
    value *= 100

    return round(value)


# Hauptfunktion zum Starten der Simulation
if __name__ == '__main__':
    # Erstelle alle Kombinationen von Maschinen und Trocknern (1 bis 20)
    tasks = [(i, j) for i in range(1, 21) for j in range(1, 21)]

    # Verwende alle CPU-Kerne für parallele Verarbeitung
    with Pool(processes=cpu_count()) as pool:
        results = pool.starmap(simulate_pair, tasks)

    # Umwandlung in 2D-Array zur Visualisierung
    report = [results[i * 20:(i + 1) * 20] for i in range(20)]
    percent_array = np.array(report)

    # Visualisiere Erfolgsrate als Heatmap
    plt.imshow(percent_array, cmap='Spectral', vmin=0, vmax=100, origin='lower')
    cbar = plt.colorbar()
    cbar.set_label('Verfügbarkeit in %')

    # Schreibe Werte in Heatmap-Zellen
    for i in range(percent_array.shape[0]):
        for j in range(percent_array.shape[1]):
            plt.text(j, i, f"{percent_array[i, j]}", ha='center', va='center', fontsize=7)

    plt.title("Waschraum Verfügbarkeit")
    plt.xlabel("Anzahl Trockner")
    plt.ylabel("Anzahl Waschmaschinen")
    plt.xticks(np.arange(percent_array.shape[1]), np.arange(1, percent_array.shape[1] + 1))
    plt.yticks(np.arange(percent_array.shape[0]), np.arange(1, percent_array.shape[0] + 1))

    plt.grid(False)
    plt.tight_layout()
    plt.show()
