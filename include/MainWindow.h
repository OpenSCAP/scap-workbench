#include "ui_MainWindow.h"
#include <QMainWindow>

class MainWindow : public QMainWindow
{
    Q_OBJECT

    public:
        explicit MainWindow(QWidget* parent = 0);
        virtual ~MainWindow();

        void clearResults();

    public slots:
        void openFile(const QString& path);
        void closeFile();
        void openFileDialog();

    private:
        Ui_MainWindow mUI;
        struct xccdf_session* mSession;
};
