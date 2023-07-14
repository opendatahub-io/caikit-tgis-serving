# Bootstrap process(optional)
~~~
yum -y install git git-lfs
git lfs install
git clone https://huggingface.co/bigscience/bloom-560m

python3 -m virtualenv venv
source venv/bin/activate

git clone https://github.com/Xaenalt/caikit-nlp
python3.9 -m pip install ./caikit-nlp/   (python 3.11 can not compile)  <pip install ./caikit-nlp>
cp ../convert.py .
./convert.py --model-path ./bloom-560m/ --model-save-path ./bloom-560m-caikit
~~~
