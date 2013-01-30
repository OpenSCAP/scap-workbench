#include <QMainWindow>

#include "ui_MainWindow.h"

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
        void reloadSession();
        void refreshProfiles();

        Ui_MainWindow mUI;
        struct xccdf_session* mSession;

    private slots:
        void checklistComboboxChanged(const QString& text);

};
