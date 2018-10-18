// Requires MorphoLibJ

// The default input and output folder
inputDir = "/dockershare/667/in/";
outputDir = "/dockershare/667/out/";

// Functional parameters
gauRad = 4;
minThreshold = 15;

arg = getArgument();
parts = split(arg, ",");

setBatchMode(true);
for(i=0; i<parts.length; i++) {
	nameAndValue = split(parts[i], "=");
	if (indexOf(nameAndValue[0], "input")>-1) inputDir=nameAndValue[1];
	if (indexOf(nameAndValue[0], "output")>-1) outputDir=nameAndValue[1];
	if (indexOf(nameAndValue[0], "radius")>-1) gauRad=nameAndValue[1];
	if (indexOf(nameAndValue[0], "min_threshold")>-1) minThreshold=nameAndValue[1];
}

images = getFileList(inputDir);

for(i=0; i<images.length; i++) {
	image = images[i];
	if (endsWith(image, ".tif")) {
		// Open image
		open(inputDir + "/" + image);
		run("Gaussian Blur 3D...", "x="+d2s(gauRad,0)+" y="+d2s(gauRad,0)+" z="+d2s(gauRad,0));
    setThreshold(d2s(minThreshold,0), 255);
    run("Convert to Mask", "method=Default background=Dark");
    run("3D Fill Holes");
    //ID = getImageID();
    run("Distance Transform Watershed 3D", "distances=[Borgefors (3,4,5)] output=[16 bits] normalize dynamic=2 connectivity=6");
    setMinAndMax(0,65535);
    run("16-bit");
		/*
		width = getWidth();
		height = getHeight();
		
		// Processing
		run("Clear Results", "");
		run("FeatureJ Laplacian", "compute smoothing="+d2s(LapRad,2));
		run("Find Maxima...", "noise="+d2s(NoiseTol,2)+" output=List light");
		
		// Export results
		newImage("Mask", "16-bit black", width, height, 1);
		for(r=0;r<nResults;r++)
		{
			XPos = getResult("X",r);
			YPos = getResult("Y",r);
			setPixel(XPos,YPos,65535);			
		}
		*/
		save(outputDir + "/" + image);
		// Cleanup
		run("Close All");
	}
}
run("Quit");







run("Gaussian Blur 3D...", "x=4 y=4 z=4");
setThreshold(15, 255);
run("Convert to Mask", "method=Default background=Dark");
run("3D Fill Holes");
ID = getImageID();
run("Distance Transform Watershed 3D", "distances=[Borgefors (3,4,5)] output=[16 bits] normalize dynamic=2 connectivity=6");
setMinAndMax(0,65535);
run("16-bit");
selectImage(ID);
close();
