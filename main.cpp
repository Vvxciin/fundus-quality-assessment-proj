#include <filesystem>
#include <iostream>

#include <opencv2/opencv.hpp>

//Vorgegebene relative Pfade im Projekt-Verzeichnis zum Finden und Speichern von Videos
const std::string INPATH = "./input/AT012.dv";
const std::string SOBPATH = "./output/AT012_sob.dv";
const std::string TESTPATH = "./output/AT012_test.dv";
const std::string LAPPATH = "./output/AT012_laplace.dv";
const std::string MASKPATH = "./output/AT012_mask.dv";

void Mask() {
    //Funktion zum Ausblenden von nichtrelevanten (kontrastarmen) Teilen des Videos
    int fourcc;
    int fps=25;
    cv::Size res;
    int frameCount=0;
    double brightness=0;

    cv::Mat inputFrame;
    cv::Mat filteredFrame;
    cv::Mat maskedFrame;
    cv::Mat mask;

    //Vorbereiten des Originalvideos und Resultat eines bereits angewendeten Kantenfilter
    cv::VideoCapture input(INPATH);
    if (!input.isOpened()) {
        std::cout << "File not found" << std::endl;
    }
    cv::VideoCapture filtered(SOBPATH);
    if (!filtered.isOpened()) {
        std::cout << "File not found" << std::endl;
    }

    //Speichern von Attributen des zu überprüfenden Videos, um die resultierenden Videos im gleichen Format zu haben
    fourcc = static_cast<int>(input.get(cv::CAP_PROP_FOURCC));
    res = cv::Size(input.get(cv::CAP_PROP_FRAME_WIDTH),input.get(cv::CAP_PROP_FRAME_HEIGHT));

    std::filesystem::remove(TESTPATH);
    cv::VideoWriter test =cv::VideoWriter(TESTPATH, fourcc, fps, res, false);

    while (true) {
        // Endlosschleife zur Frame-by-Frame-Bearbeitung der Videos
        if (!input.read(inputFrame) || !filtered.read(filteredFrame)) {
            std::cout << "End of Video" << std::endl;
            break;
        }
        //Wir arbeiten nicht mit Farbbildern, aber es muss sichergestellt werden, dass die Frames der Videos als Graustufenbild betrachtet werden
        cv::cvtColor(inputFrame, inputFrame, cv::COLOR_RGB2GRAY);
        cv::cvtColor(filteredFrame, filteredFrame, cv::COLOR_RGB2GRAY);
        cv::threshold(filteredFrame,mask,10,255,cv::THRESH_BINARY);
        //Mit dieser Maske können alle kontrastarmen Stellen der Bilder ausgeblendet werden

        cv::bitwise_and(inputFrame,mask,maskedFrame);
        test.write(maskedFrame);
        //Konsolenangabe zur Abschätzung, wie weit das Programm ist
        if (frameCount%fps == 0) std::cout << frameCount/fps << " Sekunden verlaufen." << std::endl;
        frameCount++;
        //Durchschnittshelligkeit der Maske gibt Anteil an relevanten Teilen im Video für ein Frame im Video an
        brightness+=cv::mean(mask)[0];
    }
    std::cout << "Anteil der betrachteten Pixel: " << (brightness/frameCount)/255 << "%." <<std::endl;
}

void laplace(){
    int fourcc;
    int fps=25;
    cv::Size res;
    const int BRIGHT_CAP = 128;
    int frameCount=0;
    double brightness=0;

    cv::Mat inputFrame;
    cv::Mat rawFrame;
    cv::Mat testFrame;
    cv::Mat lapFrame;
    cv::Mat endFrame;
    cv::Mat mask;
    bool validFrame;

    cv::VideoCapture input(INPATH);
    if (!input.isOpened()) {
        std::cout << "File not found" << std::endl;
    }

    //Speichern von Attributen des zu überprüfenden Videos, um die resultierenden Videos im gleichen Format zu haben
    fourcc = static_cast<int>(input.get(cv::CAP_PROP_FOURCC));
    res = cv::Size(input.get(cv::CAP_PROP_FRAME_WIDTH),input.get(cv::CAP_PROP_FRAME_HEIGHT));

    std::filesystem::remove(LAPPATH);
    cv::VideoWriter lap =cv::VideoWriter(LAPPATH, fourcc, fps, res, false);
    std::filesystem::remove(MASKPATH);
    cv::VideoWriter test =cv::VideoWriter(MASKPATH, fourcc, fps, res, false);

    while (true) {
        //Schleife zum Frame-by-Frame-Einlesen des zu überprüfenden Videos
        validFrame = input.read(inputFrame);
        if (!validFrame) {
            std::cout << "End of Video" << std::endl;
            break;
        }
        cv::cvtColor(inputFrame, inputFrame, cv::COLOR_RGB2GRAY);
        cv::GaussianBlur(inputFrame, rawFrame, cv::Size(3,3), 0);
        cv::Laplacian(rawFrame, lapFrame, CV_64F, 3);
        cv::threshold(inputFrame, inputFrame, BRIGHT_CAP, 0, cv::THRESH_TOZERO_INV); //Ausblenden von zu hellen Teilen des Videos
        cv::convertScaleAbs(lapFrame, endFrame);
        cv::threshold(endFrame, mask, 10, 255, cv::THRESH_BINARY);
        lap.write(endFrame);
        brightness+=cv::mean(mask)[0];
        test.write(mask);
        if (frameCount%fps == 0) std::cout << frameCount/fps << " Sekunden verlaufen." << std::endl;
        frameCount++;
    }
}

int main() {
        laplace();
        return 0;
}


