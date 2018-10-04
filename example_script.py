import matplotlib
matplotlib.use('Agg')
from matplotlib import pyplot as plt
import nifty.graph.rag as nrag
import vigra
import numpy as np
import os
import matplotlib.ticker

from compareMCandMWS import utils as utils
from compareMCandMWS.multicut_solvers import solve_multicut
import argparse


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('solver_type', type=str)
    args = parser.parse_args()

    root_path = "/export/home/abailoni/supervised_projs/MWS_vs_MC"
    # dataset_path = os.path.join(root_path, "cremi-dataset-crop")
    dataset_path = "/net/hciserver03/storage/abailoni/learnedHC/plain_unstruct/pureDICE_wholeTrainingSet/postprocess/inferName_v100k_repAttrHC095_B/"
    plots_path = os.path.join(root_path, "plots")
    save_path = os.path.join(root_path, "outputs")

    # Import data:
    uv_IDs  = vigra.readHDF5(os.path.join(dataset_path, "edge_data.h5"), 'uv_IDs')
    edge_costs  = vigra.readHDF5(os.path.join(dataset_path, "edge_data.h5"), 'edge_weights')
    segm  = vigra.readHDF5(os.path.join(dataset_path, "segmentation.h5"), 'data')
    raw  = vigra.readHDF5(os.path.join(dataset_path, "raw.h5"), 'data')
    gt = vigra.readHDF5(os.path.join(dataset_path, "gt.h5"), 'data')
    rag = nrag.gridRag(segm.astype('uint32'))
    print("Number of nodes and edges: ", rag.numberOfNodes, rag.numberOfEdges)


    # Compute edge sizes:
    shape = segm.shape
    fake_data = np.zeros(shape, dtype='float32')
    edge_sizes = nrag.accumulateEdgeMeanAndLength(rag, fake_data)[:, 1]
    print(edge_sizes.min(), edge_sizes.max(), edge_sizes.mean())
    edge_costs = edge_costs * edge_sizes / edge_sizes.max() * 16.

    # Solve multicut problem:
    outputs = solve_multicut(rag, edge_costs, p=1, solver_type=args.solver_type,
                             proposal_generator_type="WS",
                             )
    energy, final_node_labels, final_edge_labels, log_visitor, runtime = outputs
    print("Took {}s. Final energy: {}".format(runtime, (final_edge_labels*edge_costs).sum()))

    # Plot 1: energy vs runtime
    ncols, nrows = 1, 1
    f, ax = plt.subplots(ncols=ncols, nrows=nrows)
    ax.semilogy(log_visitor.runtimes(), -log_visitor.energies())
    ax.set_yticks([2061, 2061.10, 2061.12133])
    ax.get_yaxis().set_major_formatter(matplotlib.ticker.ScalarFormatter())
    f.savefig(os.path.join(plots_path, 'energy-runtime-{}.pdf'.format(args.solver_type)), format='pdf')

    # Plot 2: initial and final segmentation (take a 2D slice of the volume)
    final_segm = np.squeeze(utils.map_features_to_label_array(segm, np.expand_dims(final_node_labels, axis=-1)))
    ncols, nrows = 2, 1
    f, ax = plt.subplots(ncols=ncols, nrows=nrows)
    utils.plot_segm(ax[0], segm, z_slice=5, background=raw)
    utils.plot_segm(ax[1], final_segm, z_slice=5, background=raw)
    f.savefig(os.path.join(plots_path, 'final_segm.pdf'), format='pdf')

    evals = utils.cremi_score(gt, final_segm, border_threshold=None, return_all_scores=True)
    print("Scores achieved: ", evals)

    # Save some data:
    vigra.writeHDF5(final_segm.astype('uint32'), os.path.join(save_path, "final_segm_{}.h5".format(args.solver_type)), 'data')

