FROM neubiaswg5/fiji-base

RUN cd /fiji/plugins && wget -O MorphoLibJ_-1.3.6.jar https://github.com/ijpb/MorphoLibJ/releases/download/v1.3.6/MorphoLibJ_-1.3.6.jar
RUN cd /fiji/plugins && wget -O mcib3d-core3.92.jar http://imagejdocu.tudor.lu/lib/exe/fetch.php?media=plugin:stacks:3d_ij_suite:mcib3d-core3.92.jar
RUN cd /fiji/plugins && wget -O mcib3d_plugins3.92.jar http://imagejdocu.tudor.lu/lib/exe/fetch.php?media=plugin:stacks:3d_ij_suite:mcib3d_plugins3.92.jar

ADD IJNuclei3DSegmentation.ijm /fiji/macros/macro.ijm

ADD wrapper.py /app/wrapper.py

ENTRYPOINT ["python", "/app/wrapper.py"]





