from datetime import datetime
from calc import logloss, surround, avgstd
from conf import dataset_name, nb_competences_values
import random
import my_io
import json
import sys

if sys.argv[1] == 'baseline':
	from baseline import Baseline
	models = [Baseline()]
elif sys.argv[1] == 'qm':
	from qmatrix import QMatrix
	models = []
	for nb_competences in nb_competences_values:
		models.append(QMatrix(nb_competences=nb_competences))
elif sys.argv[1] == 'qmspe':
	from qmatrix import QMatrix
	q = QMatrix(nb_competences=8)
	q.load('qmatrix-cdm')
	models = [q]
elif sys.argv[1] == 'irt':
	from irt import IRT
	models = [IRT()]
else:
	from irt import IRT
	models = [IRT(criterion='MEPV')]

# n_split = 5
# budget = 20
all_student_sampled = True
models_names = [model.name for model in models]

def display(results):
	for name in results:
		print name, results[name]['mean']

def evaluate(performance, truth, replied_so_far):
	nb_questions = len(performance)
	# print [performance[i] for i in range(nb_questions) if i not in replied_so_far], [truth[i] for i in range(nb_questions) if i not in replied_so_far]
	# return logloss([performance[i] for i in range(nb_questions) if i not in replied_so_far], [truth[i] for i in range(nb_questions) if i not in replied_so_far])
	return logloss(performance, truth, replied_so_far)

def dummy_count(performance, truth, replied_so_far):
	nb_questions = len(performance)
	# print 'indecision', sum([0.4 <= performance[i] <= 0.6 for i in range(nb_questions) if i not in replied_so_far])
	return sum([(performance[i] < 0.5 and truth[i]) or (performance[i] > 0.5 and not truth[i]) for i in range(nb_questions) if i not in replied_so_far]) # Count errors

def get_results(log, god_prefix):
	results = {}
	nb_students = len(log.values()[0])
	budget = len(log.values()[0][0])
	for model in models:
		results[model.name] = {'mean': [sum(log[model.name][i][t] for i in range(nb_students)) / nb_students for t in range(budget)]}
	my_io.backup('stats-%s-%s-%s' % (dataset_name, god_prefix, datetime.now().strftime('%d%m%Y%H%M%S')), results)

def simulate(model, train_data, test_data, error_log):
	model.training_step(train_data, opt_Q=True, opt_sg=True)
	nb_students = len(test_data)
	nb_questions = len(test_data[0])
	budget = nb_questions
	if all_student_sampled:
		student_sample = range(nb_students) # All students
	error_rate = [[] for _ in range(budget)]
	for student_id in student_sample:
		# print 'Student', student_id, test_data[student_id]
		error_log.append([0] * budget)
		model.init_test()
		replied_so_far = []
		results_so_far = []
		# print 'Initial', model.predict_performance()
		# print 'Initial error', logloss(model.predict_performance(), test_data[student_id])
		for t in range(1, budget + 1):
			question_id = model.next_item(replied_so_far, results_so_far)
			# print 'Turn', t, '-> question', question_id
			replied_so_far.append(question_id)
			results_so_far.append(test_data[student_id][question_id])
			model.estimate_parameters(replied_so_far, results_so_far)
			performance = model.predict_performance()
			"""if model.name == 'QMatrix':
				print surround(model.p_test)
				print 'required', [''.join(map(lambda x: str(int(x)), model.Q[i])) for i in range(nb_questions) if i not in replied_so_far]
				print 'slip', [model.slip[i] for i in range(nb_questions) if i not in replied_so_far]
				print 'guess', [model.guess[i] for i in range(nb_questions) if i not in replied_so_far]
				print [surround(performance)[i] for i in range(nb_questions) if i not in replied_so_far]
				print [test_data[student_id][i] for i in range(nb_questions) if i not in replied_so_far]
				print evaluate(performance, test_data[student_id], replied_so_far)"""
			# print ''.join(map(lambda x: str(int(round(x))), performance))
			# print ''.join(map(lambda x: str(int(x)), test_data[student_id]))
			error_log[-1][t - 1] = evaluate(performance, test_data[student_id], replied_so_far)
			# error_rate[t - 1].append(dummy_count(performance, test_data[student_id], replied_so_far) / (len(performance) - len(replied_so_far)))
			# print '%2d' % t, error_log[-1][t - 1]
			"""if t == 38:
				print t, error_log[-1][t]
				print [performance[i] for i in range(len(performance)) if i not in replied_so_far]
				print [test_data[student_id][i] for i in range(len(performance)) if i not in replied_so_far]"""
	"""for t in range(budget):
		print error_rate[t]
		print avgstd(error_rate[t])"""

def main():
	full_dataset = my_io.load(dataset_name, prefix='data')['student_data']#[::-1]
	if dataset_name == 'sat':
		nb_questions = 20
		test_power = 80
		# question_subset = range(nb_questions)[:20]
		j = json.load(open('subset.json'))
		question_subset = j['question_subset']
		train_subset = j['train_subset']
		test_subset = sorted(set(range(296)) - set(train_subset))
		# question_subset = [2 * i for i in range(nb_questions)] # sorted(random.sample(range(len(full_dataset[0])), nb_questions))
	elif dataset_name == 'fraction':
		nb_questions = 20
		test_power = 1
		# question_subset = range(nb_questions)
		j = json.load(open('subset.json'))
		question_subset = j['question_subset']
		train_subset = j['train_subset']
		test_subset = sorted(set(range(536)) - set(train_subset))
	elif dataset_name == 'castor6e':
		nb_questions = 17
		test_power = 10000
		question_subset = range(nb_questions)
	elif dataset_name.startswith('3x2'):
		nb_questions = 3
		test_power = 10
		question_subset = range(nb_questions)
	for model in models:
		error_rate = []
		train_power = len(full_dataset) - test_power
		begin = datetime.now()
		log = {}
		if model.name == 'QMatrix':
			god_prefix = '%s-%s-%s' % (model.nb_competences, nb_questions, train_power)
		elif model.name == 'Baseline':
			god_prefix = 'baseline-%s-%s' % (nb_questions, train_power)
		elif model.criterion == 'MFI':
			god_prefix = 'irt-%s-%s' % (nb_questions, train_power)
		else:
			god_prefix = 'mepv-irt-%s-%s' % (nb_questions, train_power)
		dataset = [[full_dataset[i][j] for j in question_subset] for i in range(len(full_dataset))]
		train_dataset = dataset[:train_power]
		test_dataset = dataset[-test_power:]
		train_dataset = [dataset[i] for i in train_subset]
		test_dataset = [dataset[i] for i in test_subset]
		error_log = []
		simulate(model, train_dataset, test_dataset, error_log)
		print god_prefix
		log[model.name] = error_log
		get_results(log, god_prefix)
		my_io.backup('log-%s-%s-%s' % (dataset_name, god_prefix, datetime.now().strftime('%d%m%Y%H%M%S')), error_log)
		print datetime.now() - begin

if __name__ == '__main__':
	main()
