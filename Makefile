pipetree.dot.png: test/test_pipetree.py
	python -c "from test import test_pipetree; print(test_pipetree.pt.graph(test_pipetree).to_dot())" > pipetree.dot
	dot pipetree.dot -Tpng -O
	rm pipetree.dot
	xdg-open $@
