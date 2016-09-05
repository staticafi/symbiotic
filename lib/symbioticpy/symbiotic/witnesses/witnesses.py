#!/usr/bin/python

from lxml import etree

class GraphMLWriter(object):
    def __init__(self):

        ns = {None:'http://graphml.graphdrawing.org/xmlns/graphml'}
        self._root = etree.Element('graphml', nsmap=ns)
        self._graph = etree.SubElement(self._root, 'graph', edgedefault="directed")

        # create the entry node
        self._entry = etree.SubElement(self._graph, 'node', id='0')
        etree.SubElement(self._entry, 'data', key='entry').text = 'true'

    def parsePath(self, pathFile):
        f = open(pathFile, 'r')
        last_id=1

        ctrlelem = None
        for line in f:
            l = line.split()
            assert len(l) == 3
            #print(l)

            # create new node
            etree.SubElement(self._graph, 'node', id=str(last_id))


            # create new edge
            edge = etree.SubElement(self._graph, 'edge',
                                    source=str(last_id - 1),
                                    target=str(last_id))
            etree.SubElement(edge, 'data', key='startline').text = l[2]
            etree.SubElement(edge, 'data', key='originfile').text = l[1]
            if int(l[0]) == 0:
                # KLEE splits the true/false inverted for some reason
                control = 'condition-true'
            else:
                control = 'condition-false'

            ctrlelem = etree.SubElement(edge, 'data', key='control')
            ctrlelem.text = control

            last_id += 1

        # create the violation
        vl = etree.SubElement(self._graph, 'node', id=str(last_id))
        etree.SubElement(vl, 'data', key='violation').text = 'true'

        etree.SubElement(self._graph, 'edge',
                         source=str(last_id - 1),
                         target=str(last_id))

        # remove the control key from the last edge
        if ctrlelem is not None:
            ctrlelem.getparent().remove(ctrlelem)

        f.close()

    def dump(self):
        print(etree.tostring(self._root, pretty_print=True))

    def write(self, to):
        et = etree.ElementTree(self._root)
        et.write(to, encoding='UTF-8', method="xml",
                 pretty_print=True, xml_declaration=True)

# my $output = IO::File->new(">-");
# 
# my $writer = XML::Writer->new(OUTPUT => $output);
# 
# $writer->xmlDecl("UTF-8", "no");
# $writer->startTag("graphml", "xmlns:xsi" => "http://www.w3.org/2001/XMLSchema-instance", "xmlns" => "http://graphml.graphdrawing.org/xmlns");
# $writer->startTag("graph");
# 
# $writer->startTag("node", "id" => "A0");
# 	$writer->startTag("data", "key" => "entry");
# 		$writer->characters("true");
# 	$writer->endTag("data");
# $writer->endTag("node");
# 
# my $nid = 0;
# 
# while (<>) {
# 	chomp;
# 	/^[01] .* ([0-9]+)$/;
# 	my $line = $1;
# 
# 	$writer->startTag("node", "id" => "A" . ($nid + 1));
# 	if (eof()) {
# 		$writer->startTag("data", "key" => "violation");
# 			$writer->characters("true");
# 		$writer->endTag("data");
# 	}
# 	$writer->endTag("node");
# 
# 	$writer->startTag("edge", "source" => "A$nid",
# 			"target" => "A" . ($nid + 1));
# 		$writer->startTag("data", "key" => "startline");
# 			$writer->characters($line);
# 		$writer->endTag("data");
# 	$writer->endTag("edge");
# 
# 	$nid++;
# }
# 
# $writer->endTag("graph");
# $writer->endTag("graphml");
# $writer->end();
# $output->close();
# 
# 1
