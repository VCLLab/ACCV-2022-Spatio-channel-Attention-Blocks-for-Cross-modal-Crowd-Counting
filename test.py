import torch
import os
import argparse
from datasets.crowd import Crowd_RGBTCC, Crowd_shanghaiTechRGBD
from models.fusion import fusion_model
from utils.evaluation import eval_game, eval_relative
import logging

parser = argparse.ArgumentParser(description='Test')
parser.add_argument('--data-dir', default='/root/datasets/',
                        help='training data directory')
parser.add_argument('--dataset', default='RGBTCC',
                        help='Choose the dataset: RGBTCC or ShanghaiTechRGBD')
parser.add_argument('--save-dir', default='./checkpoints/',
                        help='model directory')
parser.add_argument('--model', default='best_model_BL_RGBTCC.pth'
                    , help='model name')

parser.add_argument('--device', default='0', help='gpu device')
args = parser.parse_args()

if __name__ == '__main__':

    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s  %(message)s",
                        datefmt="%d-%H:%M",
                        handlers=[
                            logging.StreamHandler()
                        ])
    logger = logging.getLogger()
    fh = logging.FileHandler("{0}/{1}.log".format(args.save_dir, 'test'), mode='w')
    fh.setFormatter(logging.Formatter(fmt="%(asctime)s  %(message)s", datefmt="%d-%H:%M"))
    logger.addHandler(fh)
    logger.info(' *** Test!! *** ')

    if args.dataset == 'ShanghaiTechRGBD':
        Crowd = Crowd_shanghaiTechRGBD
        data_dir = os.path.join(args.data_dir, 'ShanghaiTechRGBD')
        datasets = Crowd(os.path.join(data_dir, 'test_data'), method='test')
        dataloader = torch.utils.data.DataLoader(datasets, 1, shuffle=False, num_workers=2, pin_memory=True)

    elif args.dataset == 'RGBTCC':
        Crowd = Crowd_RGBTCC
        data_dir = os.path.join(args.data_dir, 'bayes-RGBT-CC')
        datasets = Crowd(os.path.join(data_dir, 'test'), method='test')
        dataloader = torch.utils.data.DataLoader(datasets, 1, shuffle=False,
                                                 num_workers=2, pin_memory=True)
    else:
        print("dataset error!")

    os.environ['CUDA_VISIBLE_DEVICES'] = args.device  # set vis gpu
    device = torch.device('cuda')

    model = fusion_model()
    model.to(device)
    model_path = os.path.join(args.save_dir, args.model)
    checkpoint = torch.load(model_path, device)
    model.load_state_dict(checkpoint)
    model.eval()

    print('testing...')
    # Iterate over data.
    game = [0, 0, 0, 0]
    mse = [0, 0, 0, 0]
    total_relative_error = 0

    for inputs, target, name in dataloader:
        if type(inputs) == list:
            inputs[0] = inputs[0].to(device)# RGB image
            inputs[1] = inputs[1].to(device)# T
        else:
            inputs = inputs.to(device)


        if type(inputs) == list:
            assert inputs[0].size(0) == 1
        else:
            assert inputs.size(0) == 1, 'the batch size should equal to 1 in validation mode'
        with torch.set_grad_enabled(False):
            outputs = model(inputs, args.dataset)


            # metric:game, MSE,relative
            for L in range(4):
                abs_error, square_error = eval_game(outputs, target, L)
                game[L] += abs_error
                mse[L] += square_error
            relative_error = eval_relative(outputs, target)
            total_relative_error += relative_error

    N = len(dataloader)
    game = [m / N for m in game]
    mse = [torch.sqrt(m / N) for m in mse]
    total_relative_error = total_relative_error / N

    log_str = 'Test{}, GAME0 {game0:.2f} GAME1 {game1:.2f} GAME2 {game2:.2f} GAME3 {game3:.2f} ' \
              'MSE {mse:.2f} Re {relative:.4f}, '.\
        format(N, game0=game[0], game1=game[1], game2=game[2], game3=game[3], mse=mse[0], relative=total_relative_error)

    print(log_str)
    logger.info(log_str)

