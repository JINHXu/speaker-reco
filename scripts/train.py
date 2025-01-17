import os
import torch

import pytorch_lightning as pl
from omegaconf.listconfig import ListConfig
from pytorch_lightning import seed_everything

from nemo.collections.asr.models import EncDecSpeakerLabelModel
from nemo.core.config import hydra_runner
from nemo.utils import logging
from nemo.utils.exp_manager import exp_manager

"""
Basic run (on GPU for 10 epochs for 2 class training):
EXP_NAME=sample_run
python ./speaker_reco.py --config-path='conf' --config-name='SpeakerNet_recognition_3x2x512.yaml' \
    trainer.max_epochs=10  \
    model.train_ds.batch_size=64 model.validation_ds.batch_size=64 \
    model.train_ds.manifest_filepath="<train_manifest>" model.validation_ds.manifest_filepath="<dev_manifest>" \
    model.test_ds.manifest_filepath="<test_manifest>" \
    trainer.gpus=1 \
    model.decoder.params.num_classes=2 \
    exp_manager.name=$EXP_NAME +exp_manager.use_datetime_version=False \
    exp_manager.exp_dir='./speaker_exps'
See https://github.com/NVIDIA/NeMo/blob/main/tutorials/speaker_recognition/Speaker_Recognition_Verification.ipynb for notebook tutorial
Optional: Use tarred dataset to speech up data loading.
   Prepare ONE manifest that contains all training data you would like to include. Validation should use non-tarred dataset.
   Note that it's possible that tarred datasets impacts validation scores because it drop values in order to have same amount of files per tarfile; 
   Scores might be off since some data is missing. 
   
   Use the `convert_to_tarred_audio_dataset.py` script under <NEMO_ROOT>/scripts in order to prepare tarred audio dataset.
   For details, please see TarredAudioToClassificationLabelDataset in <NEMO_ROOT>/nemo/collections/asr/data/audio_to_label.py
"""

# session crashes constantly on colab for unknown reason when it comes to training

seed_everything(42)


@hydra_runner(config_path="/Users/xujinghua/speaker-reco/conf/", config_name="SpeakerNet_recognition_3x2x512.yaml")
def main(cfg):

    # add paths to manifests to config
    cfg.model.train_ds.manifest_filepath = '/Users/xujinghua/speaker-reco/data/train.json'
    cfg.model.validation_ds.manifest_filepath = '/Users/xujinghua/speaker-reco/data/dev.json'

    # an4 test files have a different set of speakers
    cfg.model.test_ds.manifest_filepath = '/Users/xujinghua/speaker-reco/data/test_jxu.json'

    cfg.model.decoder.num_classes = 75

    os.environ["OMP_NUM_THREADS"] = '1'

    # tutorial default setting: flags
    # Let us modify some trainer configs for this demo
    # Checks if we have GPU available and uses it
    cuda = 1 if torch.cuda.is_available() else 0
    cfg.trainer.gpus = cuda

    # Reduces maximum number of epochs to 5 for quick demonstration
    cfg.trainer.max_epochs = 5

    # Remove distributed training flags
    cfg.trainer.accelerator = None

    logging.info(f'Hydra config: {cfg.pretty()}')
    trainer = pl.Trainer(**cfg.trainer)
    log_dir = exp_manager(trainer, cfg.get("exp_manager", None))
    speaker_model = EncDecSpeakerLabelModel(cfg=cfg.model, trainer=trainer)
    trainer.fit(speaker_model)

    if not trainer.fast_dev_run:
        model_path = os.path.join(log_dir, '..', 'spkr.nemo')
        speaker_model.save_to(model_path)

    if hasattr(cfg.model, 'test_ds') and cfg.model.test_ds.manifest_filepath is not None:
        gpu = 1 if cfg.trainer.gpus != 0 else 0
        trainer = pl.Trainer(gpus=gpu)
        if speaker_model.prepare_test(trainer):
            result = trainer.test(speaker_model)
            # , ckpt_path='/Users/xujinghua/NeMo/data/an4/wav/an4_clstk/dev.json')
            print(result)


if __name__ == '__main__':
    main()