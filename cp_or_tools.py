from ortools.sat.python import visualization
from ortools.sat.python import cp_model

import collections


def operators_schedule():
    model = cp_model.CpModel()

    machines_count = 8
    days_count = 360
    operators_count = 15
    job_duration = 33
    relax_duration = 23
    vacancy_duration = 7
    vacancy_count = 4
    operator_states = ['Ожидание'] + \
                      [f'Вахта на станке №{i}' for i in range(1, machines_count+1)] + \
                      ['Отдых после вахты'] + \
                      ['Отпуск']

    all_operators = range(1, operators_count+1)
    all_days = range(1, days_count+1)
    all_operator_states = range(0, len(operator_states))
    all_machines = range(1, machines_count+1)

    states = {}
    # Создаём пространство переменных из (операторы, дни, состояния)
    for o in all_operators:
        for d in all_days:
            for s in all_operator_states:
                states[(o, d, s)] = model.NewBoolVar('state_o%id%is%i' % (o, d, s))

    # Задаём условие присутствия одного оператора на каждом станке
    for d in all_days:
        for s in all_machines:
            model.AddExactlyOne(states[(o, d, s)] for o in all_operators)

    # Условие единственности состояния у оператора каждый день
    for o in all_operators:
        for d in all_days:
            model.AddExactlyOne(states[(o, d, s)] for s in all_operator_states)

    # Условие последовательности отдыха после вахты (условие составлено нечитаемо для библиотеки)
    for o in all_operators:
        for s in all_machines:
            for d in all_days:
                if states[(o, d, s)]:

                    job_start = d
                    try:
                        while job_start > 0 and states[(o, job_start-1, s)]:
                            job_start -= 1
                    except:
                        pass

                    job_end = job_start
                    try:
                        while job_end < days_count and states[(o, job_end+1, s)]:
                            job_end += 1
                    except:
                        pass

                    model.Add(job_end - job_start <= job_duration)
                    model.Add(states[(o,job_end+1,0)] and
                              sum([states[(o, i, 0)] for i in range(job_end+1,job_end+relax_duration+1)]) == relax_duration and
                              not states[(o,job_end+1+relax_duration,0)])

    # Условие недельных интервалов отпуска (условие составлено нечитаемо для библиотеки)
    for o in all_operators:
            for d in all_days:
                s = 10
                if states[(o, d, s)]:

                    vacancy_start = d
                    try:
                        while vacancy_start > 0 and states[(o, vacancy_start-1, s)]:
                            vacancy_start -= 1
                    except:
                        pass

                    vacancy_end = vacancy_start
                    try:
                        while vacancy_end < days_count and states[(o, vacancy_end+1, s)]:
                            vacancy_end += 1
                    except:
                        pass

                    model.Add(vacancy_end - vacancy_start == vacancy_duration)

    # Условие наличия 4х отпусков
    for o in all_operators:
        model.Add(sum([states[(o, d, 10)] for d in all_days]) == vacancy_duration*vacancy_count)

    # Creates the solver and solve.
    solver = cp_model.CpSolver()
    solver.parameters.linearization_level = 0
    # Enumerate all solutions.
    solver.parameters.enumerate_all_solutions = True

    class SchedulePartialSolutionPrinter(cp_model.CpSolverSolutionCallback):
        """Print intermediate solutions."""

        def __init__(self, states, operators_count, days_count, operator_states_count, limit):
            cp_model.CpSolverSolutionCallback.__init__(self)
            self._states = states
            self._operators_count = operators_count
            self._days_count = days_count
            self._operator_states_count = operator_states_count
            self._solution_count = 0
            self._solution_limit = limit

        def on_solution_callback(self):
            self._solution_count += 1
            print('Solution %i' % self._solution_count)
            for d in range(self._days_count):
                print('Day %i' % d)
                for n in range(self._operators_count):
                    is_working = False
                    for s in range(self._operator_states_count):
                        if self.Value(self._states[(n, d, s)]):
                            is_working = True
                            print('  Nurse %i works shift %i' % (n, s))
                    if not is_working:
                        print('  Nurse {} does not work'.format(n))
            if self._solution_count >= self._solution_limit:
                print('Stop search after %i solutions' % self._solution_limit)
                self.StopSearch()

        def solution_count(self):
            return self._solution_count

    # Display the first five solutions.
    solution_limit = 1
    solution_printer = SchedulePartialSolutionPrinter(states, operators_count, days_count, len(operator_states),
                                                    solution_limit)

    solver.Solve(model, solution_printer)

    # Statistics.
    print('\nStatistics')
    print('  - conflicts      : %i' % solver.NumConflicts())
    print('  - branches       : %i' % solver.NumBranches())
    print('  - wall time      : %f s' % solver.WallTime())
    print('  - solutions found: %i' % solution_printer.solution_count())


if __name__ == '__main__':
    operators_schedule()
