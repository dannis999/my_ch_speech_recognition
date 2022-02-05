
'''
Data loading.
Note:
Nine key pinyin keyboard layout sample:

`      ABC   DEF
GHI    JKL   MNO
POQRS  TUV   WXYZ

'''
from __future__ import print_function
from hyperparams import Hyperparams as hp
import codecs
import numpy as np
import re

def load_vocab():
    import pickle
    return pickle.load(open('data/vocab.pkl', 'rb'))


def load_train_data():
    '''Loads vectorized input training data'''
    pnyn2idx, idx2pnyn, hanzi2idx, idx2hanzi = load_vocab()

    print("pnyn vocabulary size is", len(pnyn2idx))
    print("hanzi vocabulary size is", len(hanzi2idx))

    xs, ys = [], []
    with codecs.open('t', 'w', 'utf-8') as fout:
        for line in codecs.open('data/zh.tsv', 'r', 'utf-8'):
            try:
                #这里生成的数据pnyn_sent, hanzi_sent是string格式的数据
                _, pnyn_sent, hanzi_sent = line.strip().split("\t")
            except ValueError:
                continue
            # 将标点符号断句，分开作为训练数据
            pnyn_sents = re.sub(u"(?<=([。，！？]))", r"|", pnyn_sent).split("|")
            hanzi_sents = re.sub(u"(?<=([。，！？]))", r"|", hanzi_sent).split("|")
            fout.write(pnyn_sent + "===" + "|".join(pnyn_sents) + "\n")

            for pnyn_sent, hanzi_sent in zip(pnyn_sents, hanzi_sents):
                #assert len(pnyn_sent)==len(hanzi_sent)
                pnyn_sent = pnyn_sent.split(' ')
                hanzi_sent = hanzi_sent.split(' ')
                if hp.minlen < len(pnyn_sent) <= hp.maxlen:
                    # 通过字典将拼音映射为数字，如果字典中没有拼音的值，则返回1,1就是定义的Unkown，out of vocabulary
                    x = [pnyn2idx.get(pnyn, 1) for pnyn in pnyn_sent] # 1: OOV
                    # 对于汉字字典，0: empty, 1: unknown, 2: blank
                    y = [hanzi2idx.get(hanzi, 1) for hanzi in hanzi_sent] # 1: OOV
                    # xs,ys返回值是一个list格式的输入和输出数据
                    xs.append(np.array(x, np.int32).tostring())
                    ys.append(np.array(y, np.int32).tostring())
    return xs, ys

def load_test_data():
    '''Embeds and vectorize words in input corpus'''
    try:
        lines = [line for line in codecs.open('eval/input.csv', 'r', 'utf-8').read().splitlines()[1:]]
    except IOError:
        raise IOError("Write the sentences you want to test line by line in `data/input.csv` file.")

    pnyn2idx, _, hanzi2idx, _ = load_vocab()

    nums, xs, ys = [], [], [] # ys: ground truth (list of string)
    for line in lines:
        num, pnyn_sent, y = line.split(",")

        nums.append(num)
        x = [pnyn2idx.get(pnyn, 1) for pnyn in pnyn_sent]  # 1: OOV
        x += [0] * (hp.maxlen - len(x))
        xs.append(x)
        ys.append(y)

    X = np.array(xs, np.int32)
    return nums, X, ys

def load_test_string(pnyn2idx, test_string):
    '''Embeds and vectorize words in user input string'''
    pnyn_sent = test_string
    pnyn_sent = pnyn_sent.split(' ')
    xs = []
    x = [pnyn2idx.get(pnyn, 1) for pnyn in pnyn_sent]
    x += [0] * (hp.maxlen - len(x))
    xs.append(x)
    X = np.array(xs, np.int32)
    return X

# 训练数据生成，格式处理
def get_batch():
    '''Makes batch queues from the training data.
    Returns:
      A Tuple of x (Tensor), y (Tensor).
      x and y have the shape [batch_size, maxlen].
    '''
    import tensorflow as tf

    # Load data
    X, Y = load_train_data()

    # Create Queues，相当于一个数据生成器，使训练可以边读数据边训练
    x, y = tf.train.slice_input_producer([tf.convert_to_tensor(X),
                                          tf.convert_to_tensor(Y)])

    x = tf.decode_raw(x, tf.int32)
    y = tf.decode_raw(y, tf.int32)

    x, y = tf.train.batch([x, y],
                          shapes=[(None,), (None,)],
                          num_threads=8,
                          batch_size=hp.batch_size,
                          capacity=hp.batch_size * 64,
                          allow_smaller_final_batch=False,
                          dynamic_pad=True)
    num_batch = len(X) // hp.batch_size

    return x, y, num_batch  # (N, None) int32, (N, None) int32, ()