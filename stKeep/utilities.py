# -*- coding: utf-8 -*-
"""

@author: chunman zuo
"""

import os
import time
import argparse
import torch
import random
import os
import numpy as np
import pandas as pd
import scanpy as sc
import scipy.sparse as sp

from sklearn.metrics import pairwise_distances
from scipy.spatial.distance import cosine

def parameter_setting():
	
	parser      = argparse.ArgumentParser(description='Spatial transcriptomics analysis by HIN')

	parser.add_argument('--inputPath',   '-IP', type = str, default = '../test_data/DLPFC_151507/',    help='data directory')	
	parser.add_argument('--outPath', '-od', type=str, default = '../test_data/DLPFC_151507/stKeep/', help='Output path')
	parser.add_argument('--utilitePath',   '-uP', type = str, default = '../utilities/',    help='data directory')	

	parser.add_argument('--spotGene',   '-sGene', type = str, default = 'Spot_gene_neighbors.txt',    help='gene neighbors for each spot')	
	parser.add_argument('--spotGroup', '-sGroup', type=str, default = 'Spot_groups.txt', help='group neighbors for each spot')
	parser.add_argument('--spotLatent',   '-sLatent', type = str, default = 'Cell_encoding_AE.txt',    help='Spot latent feaures with 50-dimensional embeddings by AE')
	parser.add_argument('--GeneLatent',   '-GeneLatent', type = str, default = None,    help='Gene latent feaures by a first HIN model')	
	parser.add_argument('--visualFeature', '-vFeature', type=str, default = 'Image_simCLR_reprensentation.txt', help='Spot visual features with 2048-dimension')
	parser.add_argument('--spatialLocation', '-sLocation', type=str, default = 'Spot_location.txt', help='spot physical location')
	parser.add_argument('--annoFile', '-aFile', type=str, default = '151507_annotation.txt', help='annotation file')
	parser.add_argument('--pos_pair', '-posP', type=str, default = 'Spot_positive_pairs.txt', help='positive pairs beween spots')
	parser.add_argument('--visual_model', '-visM', type=str, default = '128_0.5_200_128_500_model.pth', help='Spot visual model')

	parser.add_argument('--Ligands_exp', '-Ligands_exp', type=str, default = 'ligands_expression.txt', help='Expression of ligands per spot')
	parser.add_argument('--Receptors_exp', '-Receptors_exp', type=str, default = 'receptors_expression.txt', help='Expression of receptors per spot')
	parser.add_argument('--Denoised_exp', '-Denoised_exp', type=str, default = 'Denosied_normalized_expression.txt', help='Denosied and normalized gene expression data')
	
	parser.add_argument('--cci_pairs', '-cci_pairs', type=int, default = 5304, help='The number of receptors for each spot')

	parser.add_argument('--GRN_file', '-GRN_F', type=str, default = 'Gene_regulatory_network.txt', help='The gene regulatory network file')
	parser.add_argument('--PPI_file', '-PPI_F', type=str, default = 'Protein_protein_interaction_network.txt', help='The gene-gene interaction file')
	parser.add_argument('--CCC_file', '-CCC_F', type=str, default = 'Union_LRP_data.txt', help='The paired ligand-receptor file')

	parser.add_argument('--jsonFile', '-jsonF', type=str, default = 'tissue_hires_image.json', help='JSON file generated by labelme')
	
	parser.add_argument('--visMeasure',   '-visMeas', type = str, default = 'cosine',    help='Calcualte spot visual feature similarity by cosine')	
	parser.add_argument('--rnaMeasure',   '-rnaMeas', type = str, default = 'cosine',    help='Calcualte spot RNA feature similarity by cosine')	
	parser.add_argument('--locMeasure',   '-locMeas', type = str, default = 'euclidean',    help='Calcualte spot location similarity by euclidean')	

	parser.add_argument('--geneSpot',   '-geneSpot', type = str, default = 'Gene_spot_adjancy.txt',    help='spot neighbors for each gene')	
	parser.add_argument('--geneGroup', '-geneGroup', type=str, default = 'Gene_groups.txt', help='group neighbors for each gene')
	parser.add_argument('--pos_pair_gene', '-pos_pair_gene', type=str, default = 'Gene_pos_pairs.txt', help='gene-spot-gene')
	parser.add_argument('--geneName', '-geneNa', type=str, default = 'Gene_names.txt', help='Gene names')

	parser.add_argument('--weight_decay', type=float, default = 1e-6, help='weight decay')
	parser.add_argument('--eps', type=float, default = 0.01, help='eps')

	parser.add_argument('--Node_type', '-NodeT',type=int, default=3, help='The node type of spatially resolved transcriptomics data, i.e., Spot, gene, location')
	parser.add_argument('--Cell_pos_nos', '-CellPN',type=int, default=6, help='The number of positive cells for each cell')

	parser.add_argument('--sample_rate', '-sample_rate',type=list, default=[100,1], help='the number of sampling genes')
	parser.add_argument('--hidden_dim', '-hd',type=int, default=50, help='same hidden dim features for three node types of data')

	parser.add_argument('--tau', '-tau', type=float, default=0.8)
	parser.add_argument('--feat_drop', '-feat_drop', type=float, default=0.3)
	parser.add_argument('--attn_drop', '-attn_drop', type=float, default=0.5)
	parser.add_argument('--lam', '-lam', type=float, default=0.5)

	parser.add_argument('--max_training', '-maxT', type=int, default=1000, help='Max epoches for training')
	parser.add_argument('--lr', '-lr', type=float, default = 0.005, help='Learning rate')
	parser.add_argument('--lr_cci', '-lr_cci', type=float, default = 0.002, help='Learning rate')
	parser.add_argument('--l2_coef', '-l2_coef', type=float, default=0)
	parser.add_argument('--patience', '-patience', type=int, default=30)
	parser.add_argument('--Hismodel', '-Hismodel', type=str, default='SimCLR', help='utilize SimCLR or ResNet50 to extract visual features')

	parser.add_argument('--batch_size_T', '-bT', type=int, default=128, help='Batch size for transcriptomics data')
	parser.add_argument('--epoch_per_test', '-ept', type=int, default=5, help='Epoch per test')
	parser.add_argument('--lr_AET', type=float, default = 8e-05, help='Learning rate for transcriptomics data for AE model')
	parser.add_argument('--lr_AET_F', type=float, default = 8e-06, help='final learning rate for transcriptomics data for AE model')
	parser.add_argument('--max_epoch_T', '-meT', type=int, default=1000, help='Max epoches for transcriptomics data')

	parser.add_argument('--batch_size_I', '-bI', type=int, default=128, help='Batch size for spot image data')
	parser.add_argument('--image_size', '-iS', type=int, default=32, help='image size for spot image data')
	parser.add_argument('--max_epoch_I', '-meI', type=int, default=500, help='Max epoches for spot image data')
	parser.add_argument('--latent_I', '-lI',type=int, default=128, help='Feature dim for latent vector for spot image data')
	parser.add_argument('--test_prop', default=0.05, type=float, help='the proportion data for testing')
	parser.add_argument('--lr_I', type=float, default = 0.0001, help='Learning rate for spot image data')

	parser.add_argument('--save_emb', '-save_emb',  default=True, action='store_true', help="save ebedding to file")

	parser.add_argument('--use_cuda', dest='use_cuda', default=True, action='store_true', help=" whether use cuda(default: True)")
	parser.add_argument('--seed', type=int, default=200, help='Random seed for repeat results')

	parser.add_argument('--knn', '-KNN', type=int, default=7, help='K nearst neighbour include itself')

	parser.add_argument('--temperature', default=0.5, type=float, help='Temperature used in softmax')
	parser.add_argument('--k', default=200, type=int, help='Top k most similar images used to predict the label')
	
	return parser

def encode_onehot(labels):
	labels = labels.reshape(-1, 1)
	enc = OneHotEncoder()
	enc.fit(labels)
	labels_onehot = enc.transform(labels).toarray()
	return labels_onehot

def preprocess_features(features):
	"""Row-normalize feature matrix and convert to tuple representation"""
	rowsum = np.array(features.sum(1))
	r_inv = np.power(rowsum, -1).flatten()
	r_inv[np.isinf(r_inv)] = 0.
	r_mat_inv = sp.diags(r_inv)
	features = r_mat_inv.dot(features)
	return features

def normalize_adj(adj):
	"""Symmetrically normalize adjacency matrix."""
	adj = sp.coo_matrix(adj)
	rowsum = np.array(adj.sum(1))
	d_inv_sqrt = np.power(rowsum, -0.5).flatten()
	d_inv_sqrt[np.isinf(d_inv_sqrt)] = 0.
	d_mat_inv_sqrt = sp.diags(d_inv_sqrt)
	return adj.dot(d_mat_inv_sqrt).transpose().dot(d_mat_inv_sqrt).tocoo()

def sparse_mx_to_torch_sparse_tensor(sparse_mx):
	"""Convert a scipy sparse matrix to a torch sparse tensor."""
	sparse_mx = sparse_mx.tocoo().astype(np.float32)
	indices   = torch.from_numpy(np.vstack((sparse_mx.row, sparse_mx.col)).astype(np.int64))
	values    = torch.from_numpy(sparse_mx.data)
	shape     = torch.Size(sparse_mx.shape)
	return torch.sparse.FloatTensor(indices, values, shape)


def load_data_cell( args ):
	# The order of node types: cell, gene, group

	#Spot-RNA
	print("Spot-encoding")
	spot_la      = pd.read_table(args.spotLatent, header = 0, index_col = 0)
	spot_latent  = torch.FloatTensor(preprocess_features(spot_la.values))
	print(spot_latent.size())

	# Spot-gene neighbors
	print("Spot-gene neighbors")
	adj_gene     = pd.read_table(args.spotGene, header = None, index_col = None).values
	nei_gene_n   = torch.LongTensor(adj_gene)

	if args.GeneLatent is None:
		Gene_latent  = sp.eye( adj_gene.shape[1] )
		Gene_latent  = torch.FloatTensor(preprocess_features(Gene_latent).todense())
	else:
		Gene_latent  = pd.read_table(args.GeneLatent, header = None, index_col = None).values
		Gene_latent  = torch.FloatTensor(preprocess_features(Gene_latent))

	print("Gene-encoding")
	print(Gene_latent.size())

	#Spot-group 
	print("Spot-group")
	nei_group    = pd.read_table(args.spotGroup, header = 0, index_col = 0).values
	nei_group    = [torch.LongTensor(i) for i in nei_group]
	Group_laten  = sp.eye( len(set(nei_group)) )
	Group_laten  = torch.FloatTensor(preprocess_features(Group_laten).todense())

	print("Group-encoding")
	print(Group_laten.size())

	####sematic-path
	#RNA feature for adjancy
	print("RNA feature for adjancy")
	spot_rnas    = pd.read_table(args.spotLatent, header = 0, index_col = 0).values
	dist_rna     = pairwise_distances(spot_rnas, metric = args.rnaMeasure)
	row_index    = []
	col_index    = []

	sorted_knn   = np.argsort(-dist_rna)

	for index in list(range( dist_rna.shape[0] )):
		col_index.extend( sorted_knn[index, :args.knn].tolist() )
		row_index.extend( [index] * args.knn )

	adj_rna    = sp.coo_matrix( (np.ones( len(row_index) ), (row_index, col_index) ), 
								shape=( dist_rna.shape[0], dist_rna.shape[0] ), dtype=np.float32 )

	adj_rna    = sparse_mx_to_torch_sparse_tensor(normalize_adj(adj_rna))

	#visual feature for adjancy
	print("visual feature for adjancy")
	image_lat    = pd.read_table(args.visualFeature, header = 0, index_col = 0)
	dist_vis     = pairwise_distances(image_lat.values, metric = args.visMeasure)
	row_index    = []
	col_index    = []

	sorted_knn   = np.argsort(-dist_vis)

	for index in list(range( dist_vis.shape[0] )):
		col_index.extend( sorted_knn[index, :args.knn].tolist() )
		row_index.extend( [index] * args.knn )

	adj_vis    = sp.coo_matrix( (np.ones( len(row_index) ), (row_index, col_index) ), 
								shape=( dist_vis.shape[0], dist_vis.shape[0] ), dtype=np.float32 )

	adj_vis    = sparse_mx_to_torch_sparse_tensor(normalize_adj(adj_vis))
	
	#spot location for adjancy
	print("spot location for adjancy")
	spot_loc     = pd.read_table(args.spatialLocation, header = 0, index_col = 0)
	dist_loc     = pairwise_distances(spot_loc.values, metric = args.locMeasure)

	row_index    = []
	col_index    = []

	sorted_knn   = np.argsort(dist_loc)

	for index in list(range( dist_loc.shape[0] )):
		col_index.extend( sorted_knn[index, :args.knn].tolist() )
		row_index.extend( [index] * args.knn )

	adj_loc    = sp.coo_matrix( (np.ones( len(row_index) ), (row_index, col_index) ), 
								shape=( dist_loc.shape[0], dist_loc.shape[0] ), dtype=np.float32 )

	adj_loc    = sparse_mx_to_torch_sparse_tensor(normalize_adj(adj_loc))

	# reCalculate for at least three semantic paths
	pos   = pd.read_table(args.pos_pair, header = None, index_col = None).values
	pos   = torch.FloatTensor(pos)

	return [nei_gene_n, nei_group], [spot_latent, Gene_latent, Group_laten], [adj_rna, adj_vis, adj_loc], pos, spot_la.index


def load_data_RNA( args ):

	# Spot-gene neighbors
	print("gene-spot neighbors")
	adj_spot     = pd.read_table(args.geneSpot, header = None, index_col = None).values
	adj_spot     = torch.LongTensor(adj_spot)

	spot_latent  = pd.read_table(args.spotLatent, header = 0, index_col = 0).values
	spot_latent  = torch.FloatTensor(preprocess_features(spot_latent))

	print("RNA")
	Gene_latent  = sp.eye( adj_spot.shape[0] )
	Gene_latent  = torch.FloatTensor(preprocess_features(Gene_latent).todense())

	#Spot-group 
	print("gene-group")
	nei_group    = pd.read_table(args.geneGroup, header = None, index_col = None).values
	nei_group    = [torch.LongTensor(i) for i in nei_group]

	Group_laten  = sp.eye( len(set(nei_group)) )
	Group_laten  = torch.FloatTensor(preprocess_features(Group_laten).todense())

	# get positive pairs
	pos   = pd.read_table(args.pos_pair_gene, header = None, index_col = None).values
	pos   = torch.FloatTensor(pos)

	# get gene sybols
	geneSymbol = pd.read_table(args.geneName, header = None, index_col = None).values[:,0]

	return [adj_spot, nei_group], [Gene_latent, spot_latent, Group_laten], pos, geneSymbol


def load_ccc_data( args ):

	print("spot location for adjancy")
	spot_loc     = pd.read_table(args.spatialLocation, header = 0, index_col = 0)
	dist_loc     = pairwise_distances(spot_loc.values, metric = args.locMeasure)

	sorted_knn    = dist_loc.argsort(axis=1)
	selected_node = []
	#used_spots    = []
	for index in list(range( np.shape(dist_loc)[0] )):
		selected_node.append( sorted_knn[index, :11] )
		#used_spots.extend( sorted_knn[index, :11] )
	selected_node  = torch.LongTensor(selected_node)
	#used_spots     = torch.LongTensor(list(set(used_spots)))

	print("spot-ligand data")
	spots_ligand    = pd.read_table(args.Ligands_exp, header = 0, index_col = 0)
	spots_ligand_n  = torch.FloatTensor(spots_ligand.values)

	print("spot-receptor data")
	spots_recep   = pd.read_table(args.Receptors_exp, header = 0, index_col = 0)
	spots_recep_n = torch.FloatTensor(spots_recep.values)

	pos   = pd.read_table(args.pos_pair, header = None, index_col = None).values
	pos   = torch.FloatTensor(pos)

	return selected_node, spots_ligand_n, spots_recep_n, pos, spots_ligand.index, spots_ligand.columns


def normalize( adata, filter_min_counts=True, size_factors=True, 
			   normalize_input=False, logtrans_input=True):

	if filter_min_counts:
		sc.pp.filter_genes(adata, min_counts=1)
		sc.pp.filter_cells(adata, min_counts=1)

	if size_factors or normalize_input or logtrans_input:
		adata.raw = adata.copy()
	else:
		adata.raw = adata

	if logtrans_input:
		sc.pp.log1p(adata)

	if size_factors:
		adata.obs['size_factors'] = np.log( np.sum( adata.X, axis = 1 ) )
	else:
		adata.obs['size_factors'] = 1.0

	if normalize_input:
		sc.pp.scale(adata)

	return adata

def get_cell_gene_neighbors(adata, args):

	exp_data   = sp.csr_matrix.toarray(adata.X)
	mean_gene  = np.average(exp_data, axis = 0)
	matrix_adj = np.full((len(adata), len(mean_gene)), fill_value = -1)

	for z in list(range(len(adata))):
		order_gene  = (-exp_data[z,:]/mean_gene).argsort()
		exp_gene    = np.where(exp_data[z,]>0)[0]
		matrix_adj[z, :len(adata)] = order_gene[:len(adata)]

	pd.DataFrame( matrix_adj ).to_csv( args.outPath + args.spotGene, header=None, index=None, sep='\t' ) 

def get_cell_positive_pairs(adata, args):

	cell_clus     = adata.obs['Annotation'].values.astype('str')
	cell_loc      = np.column_stack(( adata.obs['imagerow'].values.tolist(), adata.obs['imagecol'].values.tolist() ))
	dist_out      = pairwise_distances(cell_loc)
	cell_cell_adj = np.zeros((len(adata), len(adata)), dtype = np.int)

	for index in list(range( np.shape(dist_out)[0] )):
		match_int  = np.where(cell_clus[index]==cell_clus)[0]
		sorted_knn = dist_out[index, match_int].argsort()
		cell_cell_adj[index, match_int[sorted_knn[:args.Cell_pos_nos]]] = 1

	pd.DataFrame( cell_cell_adj ).to_csv( args.outPath + args.pos_pair, header=None, index=None, sep='\t' )

def get_mean_by_cluster(data, cluster):

	exp_mean  = np.zeros( (np.shape(data)[1], len(set(cluster))) )
	count     = 0 

	for z in set(cluster):
		match_int         = np.where(cluster==z)[0]
		exp_mean[:,count] = np.average(data[match_int,:], axis = 0)
		count             = count + 1

	return exp_mean, list(set(cluster))


def get_gene_modules_data(adata, args, gene_select):

	exp_data            = sp.csr_matrix.toarray(adata.X)[:,gene_select]

	gene_means, uni_clu = get_mean_by_cluster(exp_data, adata.obs['classlabel'].values )
	gene_loc_nei        = np.argmax(gene_means, axis=1)

	gene_loc_nei_new    = np.array( [uni_clu[index] for index in gene_loc_nei ])

	pd.DataFrame( gene_loc_nei_new.reshape(-1,1) ).to_csv( args.outPath + args.geneGroup, header=None, index=None, sep='\t' )

	gene_spot_adj   = np.full((exp_data.shape[1], exp_data.shape[1]), fill_value = -1)

	for z, index in enumerate(gene_loc_nei_new):

		which_int   = np.where(adata.obs['classlabel'].values==index)[0]
		temp_data   = which_int[np.where(exp_data[which_int,z]>0)[0]]
		gene_spot_adj[z, :len(temp_data)] = temp_data

	pd.DataFrame( gene_spot_adj ).to_csv( args.outPath + args.geneSpot, header=None, index=None, sep='\t' )

	pd.DataFrame( adata.var_names[gene_select] ).to_csv( args.outPath + args.geneName, header=None, index=None, sep='\t' )

def get_gene_pairs(adata, args):

	exp_data    = sp.csr_matrix.toarray(adata.X)
	exp_data_n  = np.zeros( (exp_data.shape[0], exp_data.shape[1]) )
	exp_data_n[ np.where(exp_data > 0) ] = 1

	GRN  = pd.read_table(args.utilitePath + args.GRN_file, header=None, index_col=None).values
	PPI  = pd.read_table(args.utilitePath + args.PPI_file, header=None, index_col=None).values

	matrix_count  = exp_data_n.T.dot(exp_data_n)
	gene_pos_pair = np.eye( exp_data.shape[1], dtype=int )

	inter_count = []

	for index, genesymbol in enumerate(adata.var_names):

		aa = GRN[np.where(GRN[:,0]==genesymbol)[0],1].tolist()
		aa.extend( GRN[np.where(GRN[:,1]==genesymbol)[0],0].tolist() )
		aa.extend( PPI[np.where(PPI[:,0]==genesymbol)[0],1].tolist() )
		aa.extend( PPI[np.where(PPI[:,1]==genesymbol)[0],0].tolist() )

		order_g     = (-matrix_count[ index, np.where(matrix_count[index,:]>0)[0] ]).argsort()
		inter_genes = list(set(adata.var_names[ np.where(matrix_count[index,:]>0)[0] ][order_g]) & set(aa))
		res         = [adata.var_names.tolist().index(item) for item in inter_genes if item in adata.var_names.tolist()]
		inter_count.append( len(res) )

		if len(res) > 6 :

			gene_pos_pair[index, res[:6] ]  = 1

		else:
			gene_pos_pair[index, res ]  = 1

	gene_select  = np.where(np.array(inter_count) > 0)[0]
	pd.DataFrame( gene_pos_pair[gene_select, :][:, gene_select] ).to_csv( args.outPath + args.pos_pair_gene, header=None, index=None, sep='\t' )

	return gene_select


def get_CCC_data(adata, latent, args, threthold = 5):

	exp_data    = sp.csr_matrix.toarray(adata.X)
	exp_data_n  = np.zeros( (exp_data.shape[0], exp_data.shape[1]) )
	exp_data_n[ np.where(exp_data > 0) ] = 1
	sum_gene    = np.sum(exp_data_n, axis = 0)

	CCC         = pd.read_table(args.inputPath + args.CCC_file, header=None, index_col=None).values
	ligands     = list(set( adata.var_names[np.where(sum_gene>=threthold)] ) & set(CCC[:,0]))
	receptors   = list(set( adata.var_names[np.where(sum_gene>=threthold)] ) & set(CCC[:,1]))

	lrp_list    = []
	symbol      = '->'
	for index, (lig, rec) in enumerate(CCC):
		if (lig in ligands) and (rec in receptors):
			lrp_list.append( symbol.join( [lig, rec] ) )

	used_ligands_n   = []
	used_receptors_n = []

	for str in list(set(lrp_list)):
		temps = str.split( '->' )
		used_ligands_n.append( temps[0] )
		used_receptors_n.append( temps[1] )

	ligand_int     = [ adata.var_names.tolist().index(item) for item in used_ligands_n  if item in adata.var_names.tolist() ]
	receptor_int   = [ adata.var_names.tolist().index(item) for item in used_receptors_n  if item in adata.var_names.tolist() ]

	exp_data_s     = knn_smoothing(latent, 3, exp_data)
	adata.X        = sp.csr_matrix( exp_data_s )
	#sc.pp.normalize_total(adata, inplace=True)
	#sc.pp.scale(adata, max_value=10)
	#exp_data_sm    = sp.csr_matrix.toarray()

	sc.pp.normalize_total(adata, inplace=True)
	sc.pp.scale(adata, max_value=10)
	
	ligands_exp    = adata.X[:,ligand_int]
	receptors_exp  = adata.X[:,receptor_int]

	liagand_exps_n = (ligands_exp-ligands_exp.min(axis=0))/(ligands_exp.max(axis=0)-ligands_exp.min(axis=0))
	recep_exps_n   = (receptors_exp-receptors_exp.min(axis=0))/(receptors_exp.max(axis=0)-receptors_exp.min(axis=0))

	pd.DataFrame( liagand_exps_n, index = adata.obs_names.tolist(), columns=list(set(lrp_list)) ).to_csv( args.outPath + args.Ligands_exp, sep='\t' )
	pd.DataFrame( recep_exps_n, index = adata.obs_names.tolist(), columns=list(set(lrp_list)) ).to_csv( args.outPath + args.Receptors_exp, sep='\t' )
	pd.DataFrame( adata.X, index = adata.obs_names.tolist(), columns=adata.var_names.tolist() ).to_csv( args.outPath + args.Denoised_exp, sep='\t' )


def knn_smoothing(latent, k, mat):
    dist = pairwise_distances(latent)
    row = []
    col = []
    sorted_knn = dist.argsort(axis=1)
    for idx in list(range(np.shape(dist)[0])):
        col.extend(sorted_knn[idx, : k].tolist())
        row.extend([idx] * k)

    res = np.zeros((mat.shape[0], mat.shape[1]))
    for i in range(len(col)):
        res[row[i]] += mat[col[i]]

    return res

def save_checkpoint(model, folder='./saved_model/', filename='model_best.pth.tar'):
	if not os.path.isdir(folder):
		os.mkdir(folder)

	torch.save(model.state_dict(), os.path.join(folder, filename))

def load_checkpoint(file_path, model, use_cuda=False):

	if use_cuda:
		device = torch.device( "cuda" )
		model.load_state_dict( torch.load(file_path) )
		model.to(device)
		
	else:
		device = torch.device('cpu')
		model.load_state_dict( torch.load(file_path, map_location=device) )

	model.eval()
	return model

def adjust_learning_rate(init_lr, optimizer, iteration, max_lr, adjust_epoch):

	lr = max(init_lr * (0.9 ** (iteration//adjust_epoch)), max_lr)
	for param_group in optimizer.param_groups:
		param_group["lr"] = lr

	return lr   
